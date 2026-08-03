from __future__ import annotations

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.fitness_coach import FitnessCoachAgent
from src.agents.health_analyst import HealthAnalystAgent
from src.lang_guard import detect_lang, has_foreign, repair_text
from src.services.context import HealthContext

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, llm):
        self._agents: list[BaseAgent] = [
            HealthAnalystAgent(llm),
            FitnessCoachAgent(llm),
        ]

    def analyze_all(self, ctx: HealthContext) -> list[dict[str, Any]]:
        all_insights: list[dict[str, Any]] = []
        for agent in self._agents:
            try:
                insights = agent.analyze(ctx)
                all_insights.extend(insights)
                logger.info("Agent %s produced %d insights", agent.name, len(insights))
            except Exception as e:
                logger.error("Agent %s failed: %s", agent.name, e)
        return all_insights

    def chat(self, ctx: HealthContext, question: str) -> dict[str, Any]:
        summary = ctx.to_summary()
        lang = detect_lang(question)
        lang_example = (
            'Style example (user writes in Russian, answer in Russian):\n'
            'User: "Как мне восстановиться после тяжёлой недели?"\n'
            'Assistant: "Хороший вопрос. Начните с лёгкой прогулки и приоритета на сон — '
            "ваш HRV говорит, что организму нужен отдых."
            if lang == "ru"
            else 'Style example (user writes in English, answer in English):\n'
            'User: "How do I recover after a hard week?"\n'
            'Assistant: "Good question. Start with a light walk and prioritize sleep — '
            "your HRV suggests your body needs rest."
        )
        prompt = f"""You are a personal AI health & fitness coach — you have been coaching this person and know their training, sleep, and recovery in detail.
CRITICAL RULES:
- Reply 100% in the SAME language as the user's most recent message. Russian → Russian, English → English.
- Every single word must be in that language. Never use words, prefixes, or letters from any other language — no English inside Russian, no Chinese or other foreign script. If you don't know a word, paraphrase it in the user's language.
- Keep proper nouns and common technical abbreviations unchanged (Garmin, HRV, VO2max, GPS, Wi-Fi, OK).
- Never start with a greeting and never introduce yourself or mention being an AI.
- Keep it human and conversational — like a trusted coach, not a report.
- No headings, no bullet lists, no forced sections. Short paragraphs. Give the most useful answer first; don't pad.
- Use the user's real Garmin data (HRV, sleep, training load, stress, etc.) when it's relevant — but only the numbers that matter for the question, compared to their baseline. Never dump raw data.
- Tailor advice to their profile and goals. If something key is unknown, ask a quick clarifying question instead of guessing.
- Be direct but supportive. Point out risks when you see them (overtraining, poor recovery, etc.).
- {lang_example}

At the very end of your response, add exactly 3 short follow-up questions the user could ask next.
Each must start with the literal marker "SUGGEST:" on its own line.
"SUGGEST" is a technical marker — never translate it (do NOT write "ПРЕДЛОЖЕНИЕ:" or "Предложение:").
Keep each suggestion under 8 words, in the same language as the user's question.
Example:
SUGGEST: How does my sleep affect recovery?
SUGGEST: What training zone should I use tomorrow?
SUGGEST: Show my weekly heart rate trends

Here is the user's Garmin data from the last {ctx.days} days.
IMPORTANT: Sleep data is stored under THE DATE THE SLEEP ENDED — the morning you woke up, not the evening it started. For example, sleep "from August 2 to August 3" (fell asleep on the 2nd, woke up on the 3rd) is stored under August 3. So the most recent record in the list is the sleep from last night.

{summary}

User: {question}
Assistant:"""

        from src.llm import get_llm

        llm = get_llm(temperature=0.5)
        try:
            response = llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            if has_foreign(raw, lang):
                logger.info("Language guard: repairing mixed-language response")
                raw = repair_text(raw, lang, llm)
            return self._parse_response(raw)
        except Exception as e:
            logger.error("Chat failed: %s", e)
            return {
                "response": "I'm having trouble processing your request right now. Please try again later.",
                "suggestions": [],
            }

    _SUGGESTION_MARKERS = ("SUGGEST:", "ПРЕДЛОЖЕНИЕ:")

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        lines = raw.split("\n")
        response_lines = []
        suggestions: list[str] = []
        for line in lines:
            stripped = line.strip()
            upper = stripped.upper()
            marker = next(
                (m for m in AgentOrchestrator._SUGGESTION_MARKERS if upper.startswith(m)),
                None,
            )
            if marker:
                text = stripped[len(marker):].strip().strip('"\'')
                if text:
                    suggestions.append(text)
            else:
                response_lines.append(line)
        response_text = "\n".join(response_lines).strip()
        return {
            "response": response_text,
            "suggestions": suggestions[:3],
        }
