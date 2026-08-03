from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from pydantic import BaseModel

from src.config import settings
from src.db.database import get_session
from src.db.models import User
from src.garmin.client import GarminClient
from src.security import decrypt
from src.services.data_sync import DataSyncService
from src.services.proactive_alerts import check_and_alert
from src.services.sync_tasks import perform_backfill

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


class SyncBackgroundRequest(BaseModel):
    user_id: int


def _verify_internal_secret(request: Request) -> bool:
    """Verify an internal caller via the shared X-Internal-Secret header."""
    if not settings.cloud_tasks_secret:
        return False
    return request.headers.get("X-Internal-Secret", "") == settings.cloud_tasks_secret


@router.post("/sync-background")
def sync_background(req: SyncBackgroundRequest, http_request: Request) -> dict:
    """Run a full-history backfill for one user.

    Auth is the shared X-Internal-Secret header (was Cloud Tasks OIDC before
    the move off Google Cloud). Can be triggered by a background thread in the
    same process or by an external cron.
    """
    if not _verify_internal_secret(http_request):
        raise HTTPException(status_code=403, detail="Forbidden")

    ok = perform_backfill(req.user_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Background sync failed")

    return {"status": "ok", "user_id": req.user_id}


@router.post("/sync-all-active")
def sync_all_active(http_request: Request) -> dict:
    """Called by a free cron (GitHub Actions / cron-job.org) every 1-2 hours.
    Syncs recent data for all users who haven't synced in the last 3 hours.
    """
    if not _verify_internal_secret(http_request):
        raise HTTPException(status_code=403, detail="Forbidden")

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)

    session = get_session()
    try:
        users = (
            session.query(User)
            .filter(
                User.garmin_connected == True,
                User.garmin_email.isnot(None),
                User.garmin_password.isnot(None),
            )
            .all()
        )
    finally:
        session.close()

    synced = 0
    skipped = 0
    failed = 0

    for user in users:
        if user.last_sync and user.last_sync.replace(tzinfo=None) > cutoff:
            skipped += 1
            continue

        try:
            garmin_email = decrypt(user.garmin_email)
            garmin_password = decrypt(user.garmin_password)
        except Exception:
            skipped += 1
            continue

        try:
            client = GarminClient(garmin_email, garmin_password)
            client.login()
        except Exception as e:
            logger.warning("Cron sync login failed for user %s: %s", user.id, e)
            failed += 1
            continue

        sync_service = DataSyncService(client)
        try:
            sync_service.sync_user(user.id, sync_days=2)
            synced += 1
        except Exception as e:
            logger.warning("Cron sync failed for user %s: %s", user.id, e)
            failed += 1
            continue

        try:
            check_and_alert(user.id)
        except Exception:
            pass

        time.sleep(1)

    return {
        "status": "ok",
        "users_total": len(users),
        "synced": synced,
        "skipped": skipped,
        "failed": failed,
    }
