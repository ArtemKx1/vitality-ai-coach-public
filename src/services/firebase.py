from __future__ import annotations

import json
import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

from src.config import settings

logger = logging.getLogger(__name__)

_app = None


def _load_credentials() -> dict | None:
    if settings.firebase_credentials_json:
        return json.loads(settings.firebase_credentials_json)
    path = settings.firebase_credentials_path
    if path:
        path_obj = Path(path)
        if path_obj.is_file():
            with path_obj.open(encoding="utf-8") as f:
                return json.load(f)
    return None


def init_firebase() -> bool:
    global _app
    if _app is not None:
        return True

    try:
        cred_dict = _load_credentials()
    except json.JSONDecodeError:
        logger.error("FIREBASE_CREDENTIALS_JSON is not valid JSON — push disabled")
        return False

    if not cred_dict:
        logger.warning("FIREBASE_CREDENTIALS_JSON / FIREBASE_CREDENTIALS_PATH not set — push disabled")
        return False

    try:
        cred = credentials.Certificate(cred_dict)
        _app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")
        return True
    except Exception as e:
        logger.error("Failed to init Firebase: %s", e)
        return False


def send_push(user_id: int, title: str, body: str, data: dict | None = None) -> bool:
    """Send push notification to a user's device tokens.
    
    This is a low-level helper. Callers should resolve device tokens first
    via the DeviceToken table and pass them directly.
    """
    if _app is None:
        if not init_firebase():
            return False

    from src.db.database import get_session
    from src.db.models import DeviceToken

    session = get_session()
    try:
        tokens = session.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()
        if not tokens:
            logger.debug("No device tokens for user %s", user_id)
            return False

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            tokens=[t.token for t in tokens],
        )

        response = messaging.send_each_for_multicast(message)
        logger.info(
            "Push sent to user %s: %d success, %d failure",
            user_id,
            response.success_count,
            response.failure_count,
        )

        # Remove invalid tokens
        for idx, resp in enumerate(response.responses):
            if not resp.success:
                token = tokens[idx].token
                session.query(DeviceToken).filter(DeviceToken.token == token).delete()
                logger.debug("Removed invalid device token: %s", token[:20])
        session.commit()

        return response.success_count > 0
    except Exception as e:
        logger.error("Failed to send push: %s", e)
        return False
    finally:
        session.close()
