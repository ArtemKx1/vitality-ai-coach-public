from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from garminconnect import Garmin
from garminconnect import GarminConnectTooManyRequestsError

from src.garmin.models import ActivityData, DailyHealthData, DeviceData

logger = logging.getLogger(__name__)


class GarminClient:
    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password
        self._client: Garmin | None = None

    def login(self, tokenstore: str | None = None) -> None:
        self._client = Garmin(self._email, self._password)
        if tokenstore:
            try:
                self._client.client.loads(tokenstore)
                self._client._load_profile_and_settings()
                logger.info("Logged in to Garmin Connect (loaded cached tokens)")
                return
            except Exception as e:
                logger.warning("Cached Garmin tokens rejected, falling back to full login: %s", e)
        try:
            self._client.login()
        except GarminConnectTooManyRequestsError:
            logger.warning("Garmin login rate limited (429)")
            raise
        logger.info("Logged in to Garmin Connect")

    def dump_tokens(self) -> str | None:
        if not self._client:
            return None
        try:
            return self._client.client.dumps()
        except Exception:
            return None

    def fetch_daily_health(self, target_date: date) -> DailyHealthData:
        if not self._client:
            raise RuntimeError("Not logged in")

        raw = self._client.get_stats(target_date.isoformat())

        hrv_data = self._client.get_hrv_data(target_date.isoformat())
        hrv_avg = None
        hrv_status = None
        if hrv_data:
            summary = hrv_data.get("hrvSummary")
            if summary:
                hrv_avg = summary.get("lastNightAvg")
                hrv_status = summary.get("status")

        sleep_data = self._client.get_sleep_data(target_date.isoformat())
        sleep_score = None
        sleep_duration = None
        deep_sec = light_sec = rem_sec = awake_sec = None
        if sleep_data:
            daily = sleep_data.get("dailySleepDTO", {})
            sleep_duration = daily.get("sleepTimeSeconds")
            if "sleepScores" in daily:
                sleep_score = daily["sleepScores"].get("overall", {}).get("value")
            deep_sec = daily.get("deepSleepSeconds")
            light_sec = daily.get("lightSleepSeconds")
            rem_sec = daily.get("remSleepSeconds")
            awake_sec = daily.get("awakeSleepSeconds")

        body_battery_raw = self._client.get_body_battery(target_date.isoformat())
        bb_min = bb_max = None
        if body_battery_raw:
            if isinstance(body_battery_raw, list):
                # garminconnect >= 0.3 returns list of per-day entries
                for entry in body_battery_raw:
                    if isinstance(entry, dict):
                        if "bodyBatteryValuesArray" in entry:
                            pairs = entry["bodyBatteryValuesArray"]
                            vals = [p[1] for p in pairs if isinstance(p, (list, tuple)) and len(p) > 1]
                            if vals:
                                bb_min = min(vals) if bb_min is None else min(bb_min, min(vals))
                                bb_max = max(vals) if bb_max is None else max(bb_max, max(vals))
                        else:
                            c = entry.get("charged")
                            d = entry.get("drained")
                            if c is not None:
                                bb_max = c if bb_max is None else max(bb_max, c)
                            if d is not None:
                                bb_min = d if bb_min is None else min(bb_min, d)
            else:
                instances = body_battery_raw.get("bodyBatteryValues", [])
                if instances:
                    values = [i.get("charged", 0) for i in instances]
                    bb_min = min(values)
                    bb_max = max(values)

        return DailyHealthData(
            date=target_date,
            resting_heart_rate=raw.get("restingHeartRate"),
            hrv_avg=hrv_avg,
            hrv_status=hrv_status,
            sleep_score=sleep_score,
            sleep_duration_seconds=sleep_duration,
            deep_sleep_seconds=deep_sec,
            light_sleep_seconds=light_sec,
            rem_sleep_seconds=rem_sec,
            awake_seconds=awake_sec,
            stress_avg=raw.get("averageStressLevel") or raw.get("avgStressLevel"),
            body_battery_min=bb_min,
            body_battery_max=bb_max,
            steps=raw.get("totalSteps"),
            total_calories=raw.get("totalKilocalories"),
            spo2_avg=raw.get("avgSpo2"),
            respiration_avg=raw.get("avgRespirationRate"),
            raw_data=raw,
        )

    def fetch_activities(self, start: int = 0, limit: int = 20) -> list[ActivityData]:
        if not self._client:
            raise RuntimeError("Not logged in")

        raw_activities = self._client.get_activities(start, limit)
        results: list[ActivityData] = []

        for act in raw_activities:
            start_time = datetime.fromisoformat(
                act.get("startTimeLocal", act.get("startTimeGMT", "")).replace("Z", "+00:00")
            )
            activity_type = act.get("activityType", {}).get("typeKey", "unknown")

            strength_data = None
            if activity_type == "strength_training":
                try:
                    strength_data = self.fetch_strength_sets(str(act.get("activityId")))
                except Exception as e:
                    logger.warning("Failed to fetch strength sets for activity %s: %s", act.get("activityId"), e)

            results.append(
                ActivityData(
                    activity_id=str(act.get("activityId")),
                    activity_type=activity_type,
                    start_time=start_time,
                    duration_seconds=act.get("duration", 0),
                    device_id=act.get("deviceId"),
                    distance_meters=act.get("distance"),
                    avg_heart_rate=act.get("averageHR"),
                    max_heart_rate=act.get("maxHR"),
                    avg_pace_km=act.get("averagePace"),
                    elevation_gain=act.get("elevationGain"),
                    training_effect=act.get("aerobicTrainingEffect"),
                    anaerobic_effect=act.get("anaerobicTrainingEffect"),
                    vo2max=act.get("vO2MaxValue"),
                    calories=act.get("calories"),
                    avg_power=act.get("averagePower"),
                    avg_cadence=act.get("averageCadence"),
                    raw_data=act,
                    strength_sets_raw=strength_data,
                )
            )

        return results

    def fetch_strength_sets(self, activity_id: str) -> dict[str, Any] | None:
        if not self._client:
            raise RuntimeError("Not logged in")

        raw = self._client.get_activity_exercise_sets(activity_id)
        if not isinstance(raw, dict):
            logger.warning("Unexpected response type from exerciseSets API for %s: %s", activity_id, type(raw).__name__)
            return {}
        return raw

    def fetch_all_activities(self, max_pages: int = 20) -> list[ActivityData]:
        if not self._client:
            raise RuntimeError("Not logged in")

        all_activities: list[ActivityData] = []
        for page in range(max_pages):
            batch = self.fetch_activities(start=page * 20, limit=20)
            if not batch:
                break
            all_activities.extend(batch)
        logger.info("Fetched %d total activities", len(all_activities))
        return all_activities

    def fetch_activities_since(self, cutoff: datetime) -> list[ActivityData]:
        if not self._client:
            raise RuntimeError("Not logged in")

        results: list[ActivityData] = []
        for page in range(50):
            batch = self.fetch_activities(start=page * 20, limit=20)
            if not batch:
                break
            for act in batch:
                if act.start_time < cutoff:
                    return results
                results.append(act)
        return results

    def fetch_devices(self) -> list[DeviceData]:
        if not self._client:
            raise RuntimeError("Not logged in")

        raw_devices = self._client.get_devices()
        return [
            DeviceData(
                device_id=d["deviceId"],
                product_display_name=d.get("productDisplayName", "Unknown device"),
                device_type_simple_name=d.get("deviceTypeSimpleName"),
                application_key=d.get("applicationKey"),
            )
            for d in raw_devices
        ]
