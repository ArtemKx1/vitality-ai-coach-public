from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import RUNTIME_OVERRIDE_FIELDS, apply_runtime_overrides, settings

logger = logging.getLogger(__name__)


def _clean_error(e: Exception) -> str:
    """Pull a human-readable message out of a provider error payload."""
    text = str(e)
    messages = re.findall(r"'message':\s*['\"]([^'\"]*)['\"]", text)
    if messages:
        return messages[-1]
    return text[:300]

router = APIRouter(prefix="/setup", tags=["setup"])

# Providers exposed in the first-run wizard, in display order.
AVAILABLE_PROVIDERS = [
    "groq",
    "openrouter",
    "openai",
    "mistral",
    "google_ai",
    "openai_compatible",
    "ollama",
]

_PROVIDER_KEY_FIELD = {
    "groq": "groq_api_key",
    "openrouter": "openrouter_api_key",
    "openai": "openai_api_key",
    "mistral": "mistral_api_key",
    "google_ai": "google_ai_api_key",
    "openai_compatible": "openai_api_key",
    "ollama": None,
}

_PROVIDER_MODEL_FIELD = {
    "groq": "groq_model",
    "openrouter": "openrouter_models",
    "openai": "openai_model",
    "mistral": "mistral_model",
    "google_ai": "google_ai_model",
    "openai_compatible": "openai_compatible_model",
    "ollama": "ollama_model",
}


def _has_users(db) -> bool:
    from src.db.models import User

    return db.query(User).first() is not None


def _setup_locked(db) -> bool:
    """Once the first account exists, the wizard's write endpoints are locked.

    The first user claims the instance (claim-admin).
    """
    return _has_users(db)


def _llm_configured() -> bool:
    for field in _PROVIDER_KEY_FIELD.values():
        if field and getattr(settings, field):
            return True
    # Ollama counts as configured if a host is reachable is checked by the test endpoint.
    return False


class SetupStatus(BaseModel):
    setup_required: bool
    locked: bool
    llm_configured: bool
    current_provider: str
    providers: list[str]


@router.get("/status")
def setup_status() -> SetupStatus:
    from src.db.database import get_session

    db = get_session()
    try:
        locked = _setup_locked(db)
    finally:
        db.close()
    return SetupStatus(
        setup_required=not locked,
        locked=locked,
        llm_configured=_llm_configured(),
        current_provider=settings.llm_provider,
        providers=AVAILABLE_PROVIDERS,
    )


class SetupLLMRequest(BaseModel):
    provider: str
    api_key: str = ""
    model: str | None = None
    base_url: str = ""
    ollama_host: str = ""


@router.post("/llm")
def setup_llm(req: SetupLLMRequest) -> dict:
    from src.db.database import get_session

    if req.provider not in AVAILABLE_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    db = get_session()
    try:
        if _setup_locked(db):
            raise HTTPException(
                status_code=403,
                detail="Setup is locked — an account already exists. Change LLM settings via environment variables.",
            )
    finally:
        db.close()

    overrides: dict = {"llm_provider": req.provider}
    key_field = _PROVIDER_KEY_FIELD.get(req.provider)
    if key_field and req.api_key:
        overrides[key_field] = req.api_key
    if req.provider == "openai_compatible":
        if not req.base_url or not req.model:
            raise HTTPException(status_code=400, detail="OpenAI-compatible provider requires base_url and model")
        overrides["openai_compatible_base_url"] = req.base_url
        if req.api_key:
            overrides["openai_api_key"] = req.api_key
    if req.provider == "ollama":
        if req.ollama_host:
            overrides["ollama_host"] = req.ollama_host
    model_field = _PROVIDER_MODEL_FIELD.get(req.provider)
    if model_field and req.model:
        overrides[model_field] = req.model

    path = Path(settings.runtime_config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing.update({k: v for k, v in overrides.items() if k in RUNTIME_OVERRIDE_FIELDS})
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

    apply_runtime_overrides(overrides)
    from src.llm import get_llm

    get_llm.cache_clear()
    logger.info("Setup wizard: LLM provider set to %s", req.provider)
    return {"ok": True, "provider": req.provider}


class SetupLLMTestRequest(BaseModel):
    provider: str
    api_key: str = ""
    model: str | None = None
    base_url: str = ""
    ollama_host: str = ""


@router.post("/llm/test")
def test_llm(req: SetupLLMTestRequest) -> dict:
    """Validate a provider configuration WITHOUT saving it."""
    if req.provider not in AVAILABLE_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    import src.llm as llm_module

    saved = {f: getattr(settings, f) for f in RUNTIME_OVERRIDE_FIELDS}
    try:
        overrides: dict = {"llm_provider": req.provider}
        key_field = _PROVIDER_KEY_FIELD.get(req.provider)
        if key_field and req.api_key:
            overrides[key_field] = req.api_key
        if req.provider == "openai_compatible":
            if not req.base_url or not req.model:
                raise HTTPException(status_code=400, detail="OpenAI-compatible provider requires base_url and model")
            overrides["openai_compatible_base_url"] = req.base_url
            overrides["openai_compatible_model"] = req.model
            if req.api_key:
                overrides["openai_api_key"] = req.api_key
        if req.provider == "ollama":
            if req.ollama_host:
                overrides["ollama_host"] = req.ollama_host
        model_field = _PROVIDER_MODEL_FIELD.get(req.provider)
        if model_field and req.model:
            overrides[model_field] = req.model
        apply_runtime_overrides(overrides)
        llm_module.get_llm.cache_clear()
        llm = llm_module.get_llm(0.1)
        result = llm.invoke("Reply with exactly: OK")
        return {"ok": True, "provider": req.provider, "response": str(result)[:200]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=_clean_error(e)) from e
    finally:
        for k, v in saved.items():
            setattr(settings, k, v)
        llm_module.get_llm.cache_clear()
