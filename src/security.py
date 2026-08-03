from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet

from src.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_KEY = "change-me-in-production-use-a-strong-random-key"


def _derive_key() -> bytes:
    key = settings.app_secret_key
    if key == _DEFAULT_KEY:
        raise RuntimeError(
            "APP_SECRET_KEY is still the default value. Encryption is insecure. "
            "Set a strong random key: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())


def _cipher() -> Fernet:
    return Fernet(_derive_key())


def encrypt(text: str) -> str:
    if not text:
        return text
    return _cipher().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return token
    return _cipher().decrypt(token.encode()).decode()
