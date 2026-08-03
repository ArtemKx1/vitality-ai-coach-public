from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.orchestrator import AgentOrchestrator
from src.api.auth import get_current_user
from src.db.database import get_session
from src.db.models import ChatConversation, ChatMessage, Device, User
from src.lang_guard import detect_lang as detect_response_lang
from src.lang_guard import has_foreign, repair_text, strip_cjk
from src.llm import get_llm
from src.rate_limit import limiter
from src.security import decrypt as _decrypt
from src.security import encrypt as _encrypt
from src.services.context import HealthContext
from src.services.data_sync import DataSyncService
from src.services.insights import InsightsService
from src.services.sync_helper import garmin_login, sync_with_client
from src.services.sync_tasks import run_backfill
from src.services.tts import detect_lang, synthesize


def _safe_decrypt(value: str | None, fallback: str = "") -> str:
    if not value:
        return fallback
    try:
        return _decrypt(value)
    except InvalidToken:
        return fallback


def _encrypt_title(text: str) -> str:
    """Encrypt a conversation title, capping plaintext so the Fernet token fits String(255)."""
    text = text.strip()
    if not text:
        return "New Chat"
    encoded = text.encode("utf-8")[:120]
    return _encrypt(encoded.decode("utf-8", errors="ignore"))

router = APIRouter()
logger = logging.getLogger(__name__)


def _background_garmin_sync(user_id: int) -> None:
    """Run Garmin sync in background to avoid blocking chat stream."""
    try:
        session = get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if user and user.garmin_connected:
                client = garmin_login(user)
                sync_with_client(user.id, client, sync_days=2)
        finally:
            session.close()
    except Exception as e:
        logger.warning("Background Garmin sync failed for user %d: %s", user_id, e)


class ChatRequest(BaseModel):
    message: str
    days: int = 30
    conversation_id: int | None = None


class AnalysisRequest(BaseModel):
    days: int = 30


def generate_suggestions(
    user_message: str,
    has_data: bool,
    summary: str,
    profile_str: str,
    history_text: str,
    llm,
) -> list[str]:
    """Generate contextual follow-up questions based on user's question and health data."""
    lang_hint = (
        "Reply 100% in the SAME language as the user's message. "
        "Every word must be in that language — no foreign words, no letters from "
        "other scripts. Keep proper nouns and common technical terms "
        "(Garmin, HRV, VO2max) as-is."
    )

    prompt = (
        f"You are a health & fitness coach. {lang_hint}\n\n"
        f"User profile: {profile_str}\n\n"
    )
    if has_data:
        prompt += f"Health data summary:\n{summary}\n\n"
    if history_text:
        prompt += f"Conversation so far:\n{history_text}\n\n"

    prompt += (
        f"User asked: {user_message}\n\n"
        "Based on the user's health data and their question, generate 4-6 short follow-up questions "
        "the user might want to ask next. Questions should be specific, actionable, and cover different "
        "aspects (data analysis, recommendations, comparisons, trends).\n\n"
        "Rules:\n"
        "- Each question must be short (under 10 words)\n"
        "- Do NOT repeat the user's original question\n"
        "- Do NOT include greetings or filler\n"
        "- Return ONLY a JSON array of strings, nothing else\n\n"
        'Example: ["Question 1?", "Question 2?", "Question 3?", "Question 4?"]'
    )

    try:
        result = llm.invoke(prompt)
        text = result.content if hasattr(result, "content") else str(result)
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        questions = json.loads(text)
        if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
            return questions[:6]
    except Exception as e:
        logger.warning("Suggestions generation failed: %s", e)
    return []


def _run_garmin_sync(user: User, days: int | None = None) -> dict[str, Any]:
    client = garmin_login(user)
    sync_with_client(user.id, client, sync_days=days)

    alerts: list[str] = []
    try:
        from src.services.proactive_alerts import check_and_alert
        alerts = check_and_alert(user.id)
        logger.info("Proactive alerts for user %s: %s", user.id, alerts)
    except Exception as e:
        logger.warning("Proactive alerts failed for user %s: %s", user.id, e)

    now = datetime.now(timezone.utc)
    session = get_session()
    try:
        db_user = session.query(User).filter(User.id == user.id).first()
        db_user.last_sync = now
        session.commit()
        last_sync = now.isoformat() + "Z"
    finally:
        session.close()

    return {"status": "ok", "user_id": user.id, "synced_days": days, "alerts": alerts, "last_sync": last_sync}


@router.post("/sync")
@limiter.limit("5/minute")
def sync_data(
    request: Request,
    days: int | None = None,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return _run_garmin_sync(user, days=days)


@router.get("/sync/now")
@limiter.limit("5/minute")
def sync_now(request: Request, user: User = Depends(get_current_user)) -> dict[str, Any]:
    client = garmin_login(user)
    sync_with_client(user.id, client, sync_days=14, max_activities=50)

    session = get_session()
    try:
        db_user = session.query(User).filter(User.id == user.id).first()
        db_user.last_sync = datetime.now(timezone.utc)
        session.commit()
    finally:
        session.close()

    run_backfill(user.id)

    return {"status": "sync_started", "user_id": user.id, "initial_sync_complete": True}


@router.post("/analyze")
@limiter.limit("10/minute")
def analyze(
    request: Request,
    req: AnalysisRequest,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    ctx = HealthContext(user.id, days=req.days)
    if not ctx.health_records and not ctx.activities:
        raise HTTPException(404, "No data found. Sync Garmin data first.")

    llm = get_llm()
    orchestrator = AgentOrchestrator(llm)
    insights = orchestrator.analyze_all(ctx)

    svc = InsightsService()
    for ins in insights:
        svc.save_insight(
            user_id=user.id,
            category=ins.get("category", "general"),
            title=ins.get("title", "Insight"),
            content=ins.get("content", ""),
            severity=ins.get("severity", "info"),
        )

    return insights


@router.post("/chat")
@limiter.limit("20/minute")
def chat(
    request: Request,
    req: ChatRequest,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    logger.info("Chat request: user_id=%s email=%s garmin=%s days=%d",
                 user.id, user.email, user.garmin_connected, req.days)
    ctx = HealthContext(user.id, days=req.days)
    logger.info("HealthContext: records=%d activities=%d",
                 len(ctx.health_records), len(ctx.activities))
    if not ctx.health_records and not ctx.activities:
        raise HTTPException(404, "No data found. Sync Garmin data first.")

    llm = get_llm(temperature=0.7)
    orchestrator = AgentOrchestrator(llm)
    result = orchestrator.chat(ctx, req.message)

    return {
        "response": result["response"],
        "suggestions": result["suggestions"],
    }


def _save_message(conversation_id: int, role: str, content: str):
    session = get_session()
    try:
        session.add(ChatMessage(conversation_id=conversation_id, role=role, content=_encrypt(content)))
        conv = session.query(ChatConversation).filter_by(id=conversation_id).first()
        if conv:
            if role == "user" and conv.title == "New Chat":
                conv.title = _encrypt_title(content)
            conv.updated_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to save %s message for conversation %d", role, conversation_id)
    finally:
        session.close()


def _delete_conversation(conversation_id: int) -> None:
    session = get_session()
    try:
        session.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete()
        conv = session.query(ChatConversation).filter_by(id=conversation_id).first()
        if conv:
            session.delete(conv)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Failed to delete conversation %d", conversation_id)
    finally:
        session.close()


@router.post("/chat/stream")
@limiter.limit("10/minute")
def chat_stream(
    request: Request,
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    if user.garmin_connected:
        background_tasks.add_task(_background_garmin_sync, user.id)

    ctx = HealthContext(user.id, days=req.days)
    has_data = bool(ctx.health_records or ctx.activities)

    # Single session: get/create conversation + save user msg + load history
    session = get_session()
    try:
        if req.conversation_id:
            conv = session.query(ChatConversation).filter_by(id=req.conversation_id, user_id=user.id).first()
            if not conv:
                raise HTTPException(404, "Conversation not found")
            conversation_id = conv.id
        else:
            conv = ChatConversation(user_id=user.id)
            session.add(conv)
            session.commit()
            session.refresh(conv)
            conversation_id = conv.id

        session.add(ChatMessage(conversation_id=conversation_id, role="user", content=_encrypt(req.message)))
        conv = session.query(ChatConversation).filter_by(id=conversation_id).first()
        if conv:
            if conv.title == "New Chat":
                conv.title = _encrypt_title(req.message)
            conv.updated_at = datetime.now(timezone.utc)
        session.commit()

        hist_msgs = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(40)
            .all()
        )
        history_text = ""
        if hist_msgs:
            if hist_msgs[-1].role == "user" and _safe_decrypt(hist_msgs[-1].content) == req.message:
                hist_msgs = hist_msgs[:-1]
            lines = []
            for m in hist_msgs:
                role = "User" if m.role == "user" else "Assistant"
                lines.append(f"{role}: {_safe_decrypt(m.content)}")
            history_text = "\n".join(lines)
    finally:
        session.close()

    profile_parts = []
    if user.goal:
        profile_parts.append(f"Goal: {user.goal.replace('_', ' ')}")
    if user.activities:
        try:
            acts = json.loads(user.activities)
            if isinstance(acts, list):
                profile_parts.append(f"Activities: {', '.join(a.replace('_', ' ') for a in acts)}")
        except (json.JSONDecodeError, TypeError):
            profile_parts.append(f"Activities: {user.activities.replace('_', ' ')}")
    if user.fitness_level:
        profile_parts.append(f"Fitness level: {user.fitness_level}")
    if user.equipment:
        profile_parts.append(f"Equipment: {user.equipment}")
    profile_str = " | ".join(profile_parts) or "No profile set"

    is_new_conversation = not history_text
    user_lang = detect_response_lang(req.message)

    lang_example = (
        "Style example (user writes in Russian, answer in Russian):\n"
        'User: "Как мне восстановиться после тяжёлой недели?"\n'
        'Assistant: "Хороший вопрос. Начните с лёгкой прогулки и приоритета на сон — '
        "ваш HRV говорит, что организму нужен отдых."
        if user_lang == "ru"
        else "Style example (user writes in English, answer in English):\n"
        'User: "How do I recover after a hard week?"\n'
        'Assistant: "Good question. Start with a light walk and prioritize sleep — '
        "your HRV suggests your body needs rest."
    )

    system_rules = (
        "You are a personal AI health & fitness coach — you have been coaching "
        "this person and know their training, sleep, and recovery in detail.\n"
        "CRITICAL RULES:\n"
        "- Reply 100% in the SAME language as the user's most recent message "
        "(Russian → Russian, English → English).\n"
        "- Every single word must be in that language. Never use words, prefixes, or "
        "letters from any other language — no English inside Russian, no Chinese or "
        "other foreign script. If you don't know a word, paraphrase it in the user's language.\n"
        "- Keep proper nouns and common technical abbreviations unchanged "
        "(Garmin, HRV, VO2max, GPS, Wi-Fi, OK).\n"
        "- Never start with a greeting and never introduce yourself or mention being an AI.\n"
        "- Keep it human and conversational — like a trusted coach, not a report.\n"
        "- No headings, no bullet lists, no forced sections. Short paragraphs. "
        "Give the most useful answer first; don't pad.\n"
        "- Use the user's real Garmin data (HRV, sleep, training load, stress, etc.) "
        "when it's relevant — but only the numbers that matter for the question, "
        "compared to their baseline. Never dump raw data.\n"
        "- Tailor advice to their profile and goals. If something key is unknown, "
        "ask a quick clarifying question instead of guessing.\n"
        "- Be direct but supportive. Point out risks when you see them "
        "(overtraining, poor recovery, etc.).\n"
        f"- {lang_example}"
    )

    if has_data:
        summary = ctx.to_summary()
        prompt_parts = [
            f"{system_rules}\n",
            f"Here is the user's Garmin data from the last {ctx.days} days.",
            "IMPORTANT: Sleep data is stored under THE DATE THE SLEEP ENDED — the morning you woke up, not the evening it started.",
            "For example, sleep \"from August 2 to August 3\" (fell asleep on the 2nd, woke up on the 3rd) "
            "is stored under August 3. So the most recent record in the list is the sleep from last night.\n",
            f"User profile: {profile_str}\n",
            f"{summary}\n",
        ]
        if history_text:
            prompt_parts.append("Conversation so far:")
            prompt_parts.append(history_text + "\n")
        prompt_parts.append(f"User: {req.message}")
        prompt_parts.append("Assistant:")
        prompt = "\n".join(prompt_parts)
    else:
        prompt_parts = [
            f"{system_rules}\n",
            "The user hasn't connected their Garmin account yet, so there is no personal data available.\n",
            f"User profile: {profile_str}\n",
        ]
        if history_text:
            prompt_parts.append("Conversation so far:")
            prompt_parts.append(history_text + "\n")
        prompt_parts.append(f"User: {req.message}")
        prompt_parts.append("Assistant:")
        prompt = "\n".join(prompt_parts)

    llm = get_llm(temperature=0.5)

    def gen():
        nonlocal conversation_id
        full_text = ""
        had_response = False
        stream_failed = False
        try:
            if type(llm).__name__ == "OllamaLLM":
                for token in llm.stream(prompt):
                    if token:
                        token = strip_cjk(token)
                        if not token:
                            continue
                        full_text += token
                        had_response = True
                        yield f"data: {json.dumps({'token': token})}\n\n"
            else:
                for chunk in llm.stream(prompt):
                    token = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if token:
                        token = strip_cjk(token)
                        if not token:
                            continue
                        full_text += token
                        had_response = True
                        yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            stream_failed = True
            logger.error("LLM stream failed: %s", e)
            err_str = str(e).lower()
            if any(kw in err_str for kw in ("rate", "429", "limit", "throttl", "too many")):
                now = datetime.now(timezone.utc)
                reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                seconds_left = int((reset - now).total_seconds())
                hours_left = seconds_left // 3600
                minutes_left = (seconds_left % 3600) // 60
                error_msg = (
                    f"Извините, бесплатный лимит запросов на сегодня исчерпан. "
                    f"Попробуйте снова примерно через {hours_left} ч {minutes_left} мин (после полуночи UTC)."
                )
            else:
                error_msg = "Не удалось связаться с AI-сервисом. Пожалуйста, попробуйте ещё раз через минуту."
            yield f"data: {json.dumps({'token': error_msg})}\n\n"
            if not had_response and not any(m.role == "assistant" for m in hist_msgs):
                _delete_conversation(conversation_id)
                logger.info("Deleted empty conversation %d after LLM failure", conversation_id)
                return

        if stream_failed:
            yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Language guard: fix foreign words before saving so history/context stay clean
        if has_foreign(full_text, user_lang):
            logger.info("Language guard: repairing mixed-language response")
            full_text = repair_text(full_text, user_lang, llm)

        # Generate suggestions after stream completes (no extra LLM call during stream)
        try:
            summary_text = ctx.to_summary() if has_data else ""
            suggs = generate_suggestions(req.message, has_data, summary_text, profile_str, history_text, llm)
            if suggs:
                suggs = [repair_text(s, user_lang, llm) if has_foreign(s, user_lang) else s for s in suggs]
                yield f"data: {json.dumps({'suggestions': suggs})}\n\n"
        except Exception:
            pass

        yield f"data: {json.dumps({'conversation_id': conversation_id})}\n\n"
        yield "data: [DONE]\n\n"

        _save_message(conversation_id, "assistant", full_text)
    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/chat/conversations")
def list_conversations(
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    session = get_session()
    try:
        convs = (
            session.query(ChatConversation)
            .filter(
                ChatConversation.user_id == user.id,
                ChatConversation.id.in_(
                    session.query(ChatMessage.conversation_id).filter(ChatMessage.role == "assistant")
                ),
            )
            .order_by(ChatConversation.updated_at.desc())
            .limit(30)
            .all()
        )
        return [
            {
                "id": c.id,
                "title": _safe_decrypt(c.title, "New Chat") if c.title and c.title != "New Chat" else c.title,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convs
        ]
    finally:
        session.close()


@router.post("/chat/conversations")
def create_conversation(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    session = get_session()
    try:
        conv = ChatConversation(user_id=user.id)
        session.add(conv)
        session.commit()
        session.refresh(conv)
        return {"id": conv.id, "title": _safe_decrypt(conv.title, "New Chat") if conv.title and conv.title != "New Chat" else conv.title, "created_at": conv.created_at.isoformat()}
    finally:
        session.close()


@router.get("/chat/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    offset: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    session = get_session()
    try:
        conv = session.query(ChatConversation).filter_by(id=conversation_id, user_id=user.id).first()
        if not conv:
            raise HTTPException(404, "Conversation not found")
        msgs = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        msgs.reverse()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": _safe_decrypt(m.content),
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ]
    finally:
        session.close()


@router.delete("/chat/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    session = get_session()
    try:
        conv = session.query(ChatConversation).filter_by(id=conversation_id, user_id=user.id).first()
        if not conv:
            raise HTTPException(404, "Conversation not found")
        _delete_conversation(conversation_id)
        return {"status": "ok"}
    finally:
        session.close()


@router.patch("/chat/conversations/{conversation_id}")
def update_conversation(
    conversation_id: int,
    body: dict[str, str],
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    session = get_session()
    try:
        conv = session.query(ChatConversation).filter_by(id=conversation_id, user_id=user.id).first()
        if not conv:
            raise HTTPException(404, "Conversation not found")
        if "title" in body:
            conv.title = _encrypt_title(body["title"])
        conv.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(conv)
        return {"id": conv.id, "title": _safe_decrypt(conv.title, "New Chat") if conv.title and conv.title != "New Chat" else conv.title, "updated_at": conv.updated_at.isoformat()}
    finally:
        session.close()


class TTSRequest(BaseModel):
    text: str


@router.post("/tts")
@limiter.limit("30/minute")
def text_to_speech(
    request: Request,
    req: TTSRequest,
    user: User = Depends(get_current_user),
):
    if not req.text.strip():
        raise HTTPException(400, "Text is required")
    audio = synthesize(req.text)
    from fastapi.responses import Response
    return Response(content=audio, media_type="audio/mpeg")


@router.get("/insights")
def get_insights(
    user: User = Depends(get_current_user),
) -> list[dict]:
    svc = InsightsService()
    return svc.get_recent(user.id)


@router.get("/devices")
def list_devices(
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    session = get_session()
    try:
        devices = (
            session.query(Device)
            .filter(Device.user_id == user.id)
            .order_by(Device.last_synced_at.desc())
            .all()
        )
        return [
            {
                "id": d.id,
                "device_id": d.device_id,
                "display_name": d.display_name,
                "type_name": d.type_name,
                "last_synced_at": d.last_synced_at.isoformat() + "Z" if d.last_synced_at else None,
            }
            for d in devices
        ]
    finally:
        session.close()


@router.get("/health")
def get_health_summary(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    ctx = HealthContext(user.id, days=7)
    return {
        "user_id": user.id,
        "days_of_data": len(ctx.health_records),
        "recent_activities": len(ctx.activities),
        "data": {
            "health": ctx.health_records,
            "activities": ctx.activities,
        },
    }


@router.get("/health/range")
def health_range(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return DataSyncService.get_data_range(user.id)
