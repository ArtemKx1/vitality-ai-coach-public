from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Iterator

from langchain_openai import ChatOpenAI
from langchain_core.outputs import ChatGenerationChunk

from src.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES_PER_MODEL = 2
_RETRY_BASE_DELAY = 3  # seconds


def _is_rate_limited(e: Exception) -> bool:
    err_str = str(e).lower()
    return any(kw in err_str for kw in ("rate", "429", "limit", "throttl", "too many"))


class FallbackLLM:
    """Wraps multiple ChatOpenAI instances with automatic failover on rate limits."""

    def __init__(self, llms: list[ChatOpenAI]):
        self.llms = llms
        self._current = 0

    @property
    def model_name(self) -> str:
        return self.llms[self._current].model_name

    def _call_with_retry(self, method: str, prompt: str, **kwargs):
        """Try a model with retries on rate limit, then fall through."""
        for i in range(self._current, len(self.llms)):
            llm = self.llms[i]
            last_err = None
            for attempt in range(_MAX_RETRIES_PER_MODEL):
                try:
                    logger.info("Trying model: %s (attempt %d)", llm.model_name, attempt + 1)
                    result = getattr(llm, method)(prompt, **kwargs)
                    self._current = i
                    return result
                except Exception as e:
                    last_err = e
                    if _is_rate_limited(e):
                        delay = _RETRY_BASE_DELAY * (attempt + 1)
                        logger.warning("Rate limited on %s (attempt %d), retrying in %ds", llm.model_name, attempt + 1, delay)
                        time.sleep(delay)
                        continue
                    raise
            logger.warning("All retries exhausted for %s", llm.model_name)
        raise last_err or Exception("All models failed")

    def stream(self, prompt: str) -> Iterator[ChatGenerationChunk]:
        errors = []
        for i in range(self._current, len(self.llms)):
            llm = self.llms[i]
            last_err = None
            for attempt in range(_MAX_RETRIES_PER_MODEL):
                try:
                    logger.info("Trying model: %s (attempt %d)", llm.model_name, attempt + 1)
                    for chunk in llm.stream(prompt):
                        yield chunk
                    self._current = i
                    return
                except Exception as e:
                    last_err = e
                    if _is_rate_limited(e):
                        delay = _RETRY_BASE_DELAY * (attempt + 1)
                        logger.warning("Rate limited on %s (attempt %d), retrying in %ds", llm.model_name, attempt + 1, delay)
                        time.sleep(delay)
                        continue
                    raise
            errors.append(str(last_err))
        raise Exception(f"All models failed: {'; '.join(errors)}")

    def invoke(self, prompt: str):
        return self._call_with_retry("invoke", prompt)


@lru_cache(maxsize=8)
def get_llm(temperature: float = 0.3):
    provider = settings.llm_provider

    if provider == "ollama":
        from src.ollama_provider import OllamaLLM
        logger.info("Using Ollama local LLM: %s (%s)", settings.ollama_model, settings.ollama_host)
        return OllamaLLM(model=settings.ollama_model, temperature=temperature, host=settings.ollama_host)

    if provider == "openrouter" or (provider == "auto" and settings.openrouter_api_key):
        model_names = [m.strip() for m in settings.openrouter_models.split(",") if m.strip()]
        llms = [
            ChatOpenAI(
                model=m,
                temperature=temperature,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=45,
                max_retries=0,
            )
            for m in model_names
        ]
        # Add Mistral as fallback if configured
        if settings.mistral_api_key:
            llms.append(
                ChatOpenAI(
                    model=settings.mistral_model,
                    temperature=temperature,
                    api_key=settings.mistral_api_key,
                    base_url="https://api.mistral.ai/v1",
                    timeout=20,
                    max_retries=0,
                )
            )
            logger.info("Added Mistral as fallback for OpenRouter")
        if provider == "auto":
            logger.info("Auto-select: using OpenRouter with %d models", len(llms))
        else:
            logger.info("Using OpenRouter: %s", " -> ".join(model_names))
        return FallbackLLM(llms)

    if provider == "mistral" or (provider == "auto" and settings.mistral_api_key):
        if provider == "auto":
            logger.info("Auto-select: using Mistral LLM")
        else:
            logger.info("Using Mistral LLM: %s", settings.mistral_model)
        return ChatOpenAI(
            model=settings.mistral_model,
            temperature=temperature,
            api_key=settings.mistral_api_key,
            base_url="https://api.mistral.ai/v1",
        )

    if provider == "groq" or (provider == "auto" and settings.groq_api_key):
        if provider == "auto":
            logger.info("Auto-select: using Groq LLM")
        else:
            logger.info("Using Groq LLM: %s", settings.groq_model)
        return ChatOpenAI(
            model=settings.groq_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    if provider == "google_ai" or (provider == "auto" and settings.google_ai_api_key):
        if provider == "auto":
            logger.info("Auto-select: using Google AI LLM")
        else:
            logger.info("Using Google AI LLM: %s", settings.google_ai_model)
        return ChatOpenAI(
            model=settings.google_ai_model,
            temperature=temperature,
            api_key=settings.google_ai_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        )

    if provider == "openai_compatible" or (provider == "auto" and settings.openai_compatible_base_url):
        if not settings.openai_compatible_base_url or not settings.openai_compatible_model:
            raise ValueError(
                "LLM_PROVIDER=openai_compatible requires OPENAI_COMPATIBLE_BASE_URL and OPENAI_COMPATIBLE_MODEL"
            )
        if provider == "auto":
            logger.info("Auto-select: using OpenAI-compatible LLM at %s", settings.openai_compatible_base_url)
        else:
            logger.info(
                "Using OpenAI-compatible LLM: %s at %s",
                settings.openai_compatible_model,
                settings.openai_compatible_base_url,
            )
        return ChatOpenAI(
            model=settings.openai_compatible_model,
            temperature=temperature,
            api_key=settings.openai_api_key or "not-needed",
            base_url=settings.openai_compatible_base_url.rstrip("/"),
        )

    if provider == "openai" or (provider == "auto" and settings.openai_api_key):
        if provider == "auto":
            logger.info("Auto-select: using OpenAI LLM")
        else:
            logger.info("Using OpenAI LLM")
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

    if provider == "auto":
        raise ValueError(
            "No LLM configured. Set LLM_PROVIDER and its key in .env — e.g. "
            "LLM_PROVIDER=groq + GROQ_API_KEY, LLM_PROVIDER=openrouter + OPENROUTER_API_KEY, "
            "LLM_PROVIDER=openai + OPENAI_API_KEY, LLM_PROVIDER=mistral + MISTRAL_API_KEY, "
            "LLM_PROVIDER=google_ai + GOOGLE_AI_API_KEY, "
            "LLM_PROVIDER=openai_compatible + OPENAI_COMPATIBLE_BASE_URL + OPENAI_COMPATIBLE_MODEL, "
            "or LLM_PROVIDER=ollama + local Ollama."
        )

    raise ValueError(f"Unknown LLM provider: {provider}")
