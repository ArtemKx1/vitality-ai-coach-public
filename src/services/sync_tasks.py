from __future__ import annotations

import logging
import threading

from src.db.database import get_session
from src.db.models import User
from src.garmin.client import GarminClient
from src.security import decrypt
from src.services.data_sync import MAX_HISTORY_DAYS, DataSyncService
from src.services.proactive_alerts import check_and_alert

logger = logging.getLogger(__name__)


def perform_backfill(user_id: int) -> bool:
    """Run a full-history backfill sync for a user. Returns True on success."""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user or not user.garmin_email or not user.garmin_password:
            logger.info("Backfill skipped for user %s: no Garmin credentials", user_id)
            return False

        garmin_email = decrypt(user.garmin_email)
        garmin_password = decrypt(user.garmin_password)
    finally:
        session.close()

    try:
        client = GarminClient(garmin_email, garmin_password)
        client.login()
    except Exception as e:
        logger.error("Garmin login failed in backfill for user %s: %s", user_id, e)
        return False

    sync_service = DataSyncService(client)
    try:
        sync_service.sync_user(user_id, sync_days=MAX_HISTORY_DAYS)
        logger.info("Backfill sync completed for user %s", user_id)
    except Exception as e:
        logger.error("Backfill sync failed for user %s: %s", user_id, e)
        return False

    try:
        alerts = check_and_alert(user_id)
        if alerts:
            logger.info("Proactive alerts triggered for user %s: %s", user_id, alerts)
    except Exception as e:
        logger.warning("Proactive alerts failed for user %s: %s", user_id, e)

    return True


def run_backfill(user_id: int) -> bool:
    """Run a backfill in a background thread (replaces Google Cloud Tasks).

    On hosts with scale-to-zero (Render free), the instance stays up for at
    least ~15 minutes after the triggering request, so the daemon thread has
    time to finish. The periodic /internal/sync-all-active cron recovers any
    backfill that gets cut short.
    """
    thread = threading.Thread(
        target=perform_backfill,
        args=(user_id,),
        daemon=True,
        name=f"backfill-{user_id}",
    )
    thread.start()
    logger.info("Started background backfill thread for user %s", user_id)
    return True
