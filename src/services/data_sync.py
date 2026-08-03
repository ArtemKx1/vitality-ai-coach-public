from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from src.db.database import get_session
from src.db.models import Activity, DailyHealth, Device, User
from src.garmin.client import GarminClient
from src.garmin.models import ActivityData, DailyHealthData, DeviceData

logger = logging.getLogger(__name__)

MAX_HISTORY_DAYS = 365
DAY_DELAY = 0.3


class DataSyncService:
    def __init__(self, client: GarminClient):
        self._client = client

    def sync_user(
        self,
        user_id: int,
        sync_activities: bool = True,
        sync_days: int | None = None,
        max_activities: int | None = None,
    ) -> None:
        session = get_session()

        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error("User %s not found", user_id)
                return

            self._sync_devices(session, user_id)

            today = date.today()

            if sync_days is not None:
                health_start = today - timedelta(days=sync_days)
            else:
                latest_health = (
                    session.query(func.max(DailyHealth.date))
                    .filter(DailyHealth.user_id == user_id)
                    .scalar()
                )
                if latest_health is not None:
                    health_start = latest_health + timedelta(days=1)
                    if health_start > today:
                        health_start = today
                else:
                    health_start = today - timedelta(days=7)

            existing_dates = {
                row[0] for row in session.query(DailyHealth.date)
                .filter(DailyHealth.user_id == user_id, DailyHealth.date >= health_start)
                .all()
            }
            days_to_fetch = (today - health_start).days + 1
            for i in range(days_to_fetch):
                target_date = health_start + timedelta(days=i)
                if target_date in existing_dates:
                    is_stale = (today - target_date).days <= 2
                    if not is_stale:
                        continue

                try:
                    health = self._client.fetch_daily_health(target_date)
                    self._save_health(session, user_id, health)
                except Exception as e:
                    logger.warning("Failed to sync health for %s: %s", target_date, e)

                if i < days_to_fetch - 1:
                    time.sleep(DAY_DELAY)

            if sync_activities:
                if sync_days is not None:
                    activity_cutoff = datetime.combine(today - timedelta(days=sync_days), datetime.min.time())
                    all_acts = self._client.fetch_activities_since(activity_cutoff)
                else:
                    latest_act_time = (
                        session.query(func.max(Activity.start_time))
                        .filter(Activity.user_id == user_id)
                        .scalar()
                    )
                    if latest_act_time is None:
                        all_acts = self._client.fetch_all_activities()
                    else:
                        all_acts = self._client.fetch_activities_since(latest_act_time)

                if max_activities is not None and len(all_acts) > max_activities:
                    all_acts = all_acts[:max_activities]

                existing_ids = {
                    row[0] for row in session.query(Activity.activity_id)
                    .filter(Activity.user_id == user_id)
                    .all()
                }
                for act in all_acts:
                    if act.activity_id in existing_ids:
                        is_recent = (today - act.start_time.date()).days <= 2
                        if not is_recent:
                            continue
                        session.query(Activity).filter(
                            Activity.user_id == user_id,
                            Activity.activity_id == act.activity_id,
                        ).delete()
                    self._save_activity(session, user_id, act)

            stale = (
                session.query(Activity)
                .filter(
                    Activity.user_id == user_id,
                    Activity.activity_type == "strength_training",
                    Activity.strength_data.is_(None),
                )
                .all()
            )
            backfilled = 0
            for act in stale:
                try:
                    raw = self._client.fetch_strength_sets(act.activity_id)
                    act.strength_data = json.dumps(raw) if raw is not None else "null"
                    backfilled += 1
                    time.sleep(0.2)
                except Exception as e:
                    logger.warning("Failed to backfill strength sets for activity %s: %s", act.activity_id, e)
            if stale:
                logger.info("Backfilled strength sets for %d/%d stale activities (user %s)", backfilled, len(stale), user_id)

            user.last_sync = datetime.now(timezone.utc)
            try:
                session.commit()
                logger.info("Synced data for user %s", user_id)
            except IntegrityError:
                session.rollback()
                logger.warning("Sync commit failed due to conflict for user %s (will retry later)", user_id)

        finally:
            session.close()

    @staticmethod
    def get_data_range(user_id: int) -> dict[str, Any]:
        session = get_session()
        try:
            row = (
                session.query(
                    func.min(DailyHealth.date),
                    func.max(DailyHealth.date),
                    func.count(DailyHealth.id),
                )
                .filter(DailyHealth.user_id == user_id)
                .first()
            )
            earliest, latest, count = row if row else (None, None, 0)

            return {
                "earliest_date": earliest.isoformat() if earliest else None,
                "latest_date": latest.isoformat() if latest else None,
                "total_days": count or 0,
            }
        finally:
            session.close()

    def _save_health(self, session, user_id: int, data: DailyHealthData) -> None:
        session.query(DailyHealth).filter(
            DailyHealth.user_id == user_id,
            DailyHealth.date == data.date,
        ).delete()
        record = DailyHealth(
            user_id=user_id,
            date=data.date,
            resting_heart_rate=data.resting_heart_rate,
            hrv_avg=data.hrv_avg,
            hrv_status=data.hrv_status,
            sleep_score=data.sleep_score,
            sleep_duration_seconds=data.sleep_duration_seconds,
            deep_sleep_seconds=data.deep_sleep_seconds,
            light_sleep_seconds=data.light_sleep_seconds,
            rem_sleep_seconds=data.rem_sleep_seconds,
            awake_seconds=data.awake_seconds,
            stress_avg=data.stress_avg,
            body_battery_min=data.body_battery_min,
            body_battery_max=data.body_battery_max,
            steps=data.steps,
            total_calories=data.total_calories,
            spo2_avg=data.spo2_avg,
            respiration_avg=data.respiration_avg,
        )
        session.add(record)

    def _sync_devices(self, session, user_id: int) -> None:
        try:
            devices = self._client.fetch_devices()
        except Exception as e:
            logger.warning("Failed to fetch devices: %s", e)
            return

        for d in devices:
            existing = (
                session.query(Device)
                .filter(Device.user_id == user_id, Device.device_id == d.device_id)
                .first()
            )
            if existing:
                existing.display_name = d.product_display_name
                existing.type_name = d.device_type_simple_name
                existing.last_synced_at = datetime.now(timezone.utc)
            else:
                session.add(
                    Device(
                        user_id=user_id,
                        device_id=d.device_id,
                        display_name=d.product_display_name,
                        type_name=d.device_type_simple_name,
                    )
                )
        session.commit()

    def _save_activity(self, session, user_id: int, data: ActivityData) -> None:
        strength_json = json.dumps(data.strength_sets_raw) if data.strength_sets_raw is not None else None
        raw_json = json.dumps(data.raw_data) if data.raw_data is not None else None
        record = Activity(
            user_id=user_id,
            activity_id=data.activity_id,
            activity_type=data.activity_type,
            start_time=data.start_time,
            duration_seconds=data.duration_seconds,
            distance_meters=data.distance_meters,
            avg_heart_rate=data.avg_heart_rate,
            max_heart_rate=data.max_heart_rate,
            avg_pace_km=data.avg_pace_km,
            elevation_gain=data.elevation_gain,
            training_effect=data.training_effect,
            anaerobic_effect=data.anaerobic_effect,
            vo2max=data.vo2max,
            calories=data.calories,
            avg_power=data.avg_power,
            avg_cadence=data.avg_cadence,
            device_id=data.device_id,
            raw_data=raw_json,
            strength_data=strength_json,
        )
        session.add(record)
