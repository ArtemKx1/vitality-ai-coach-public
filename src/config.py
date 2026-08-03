from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "change-me-in-production-use-a-strong-random-key"

# Fields the first-run setup wizard may write to data/config.json.
# These override environment variables at runtime (not persisted to .env).
RUNTIME_OVERRIDE_FIELDS = frozenset({
    "llm_provider",
    "groq_api_key",
    "groq_model",
    "openrouter_api_key",
    "openrouter_models",
    "openai_api_key",
    "openai_model",
    "google_ai_api_key",
    "google_ai_model",
    "mistral_api_key",
    "mistral_model",
    "openai_compatible_base_url",
    "openai_compatible_model",
    "ollama_model",
    "ollama_host",
    "garmin_email",
    "garmin_password",
})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.app_secret_key == _DEFAULT_SECRET:
            logger.error(
                "APP_SECRET_KEY is the default value! "
                "Set APP_SECRET_KEY in environment or .env. "
                "Generate one: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )

    garmin_email: str = ""
    garmin_password: str = ""

    llm_provider: str = "auto"
    ollama_model: str = "gemma4:e4b"
    ollama_host: str = "http://localhost:11434"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str = ""
    openrouter_models: str = "google/gemma-4-31b-it:free,nvidia/nemotron-3-super-120b-a12b:free,meta-llama/llama-3.3-70b-instruct:free"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_compatible_base_url: str = ""
    openai_compatible_model: str = ""
    google_ai_api_key: str = ""
    google_ai_model: str = "gemini-2.0-flash"
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"

    database_url: str = "sqlite:///./data/garmin_coach.db"
    app_secret_key: str = "change-me-in-production-use-a-strong-random-key"
    log_level: str = "INFO"

    firebase_credentials_path: str = ""
    firebase_credentials_json: str = ""  # inline JSON for Render / Docker

    # CORS — comma-separated list of allowed origins
    # In production: https://your-domain.com
    # In dev: http://localhost:5174,http://localhost:3000
    allowed_origins: str = "http://localhost:5174,http://localhost:3000,http://localhost:8000"

    gcp_project: str = ""
    gcp_project_number: str = ""
    gcp_location: str = "us-central1"
    backend_url: str = ""
    cloud_tasks_secret: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""

    # Base path where the built SPA is mounted (must match the frontend's VITE_BASE).
    # Self-host: "/" — the app is served at the site root.
    # Hosted (e.g. GitHub Pages subpath): "/garmin-ai-coach".
    frontend_base: str = "/"

    runtime_config_path: str = "data/config.json"


settings = Settings()


def apply_runtime_overrides(data: dict) -> None:
    """Apply values from data/config.json onto the live settings singleton.

    Only whitelisted fields are applied, so the wizard can never override
    operational settings (database, secret, CORS).
    """
    for key, value in data.items():
        if key in RUNTIME_OVERRIDE_FIELDS and value is not None:
            setattr(settings, key, value)
            logger.info("Runtime override: %s", key)


def load_runtime_overrides() -> None:
    path = Path(settings.runtime_config_path)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read %s — ignoring", path)
        return
    apply_runtime_overrides(data)
