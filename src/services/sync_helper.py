from __future__ import annotations

import logging

from fastapi import HTTPException

from src.db.database import get_session
from src.db.models import User
from garminconnect import GarminConnectTooManyRequestsError

from src.garmin.client import GarminClient
from src.security import decrypt
from src.services.data_sync import DataSyncService

logger = logging.getLogger(__name__)


def garmin_login(user: User) -> GarminClient:
    if not user.garmin_connected or not user.garmin_email or not user.garmin_password:
        raise HTTPException(400, "Garmin account not connected")
    try:
        garmin_email = decrypt(user.garmin_email)
        garmin_password = decrypt(user.garmin_password)
    except Exception as e:
        logger.error("Failed to decrypt Garmin credentials for user %s: %s", user.id, e)
        raise HTTPException(500, "Failed to decrypt Garmin credentials")

    client = GarminClient(garmin_email, garmin_password)
    try:
        client.login(tokenstore=user.garmin_tokens)
    except GarminConnectTooManyRequestsError:
        logger.warning("Garmin rate limited (429) for user %s", user.id)
        raise HTTPException(status_code=429, detail="Garmin API rate limit reached. Please wait a few minutes and try again.")
    except Exception as e:
        logger.warning("Garmin login failed for user %s: %s", user.id, e)
        raise HTTPException(status_code=401, detail="Garmin login failed. Check your credentials.")

    try:
        fresh = client.dump_tokens()
        if fresh:
            session = get_session()
            try:
                db_user = session.query(User).filter(User.id == user.id).first()
                if db_user and fresh != db_user.garmin_tokens:
                    db_user.garmin_tokens = fresh
                    session.commit()
            finally:
                session.close()
    except Exception as e:
        logger.warning("Failed to persist Garmin tokens for user %s: %s", user.id, e)

    return client


def sync_with_client(user_id: int, client: GarminClient, sync_days: int | None = None, max_activities: int | None = None) -> None:
    sync_service = DataSyncService(client)
    try:
        sync_service.sync_user(user_id, sync_days=sync_days, max_activities=max_activities)
    except Exception as e:
        logger.error("Sync failed for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Data sync failed. Please try again.")
