from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

from src.db.database import get_session
from src.db.models import Activity, DailyHealth
from src.garmin.models import parse_strength_sets_from_raw

logger = logging.getLogger(__name__)


class HealthContext:
    def __init__(self, user_id: int, days: int = 14):
        self.user_id = user_id
        self.days = days
        self._parsed_exercises: dict[str, list[dict[str, Any]]] = {}
        self.health_records: list[dict[str, Any]] = []
        self.activities: list[dict[str, Any]] = []
        self._summary: str | None = None
        self._load()

    def _load(self) -> None:
        session = get_session()
        try:
            cutoff = date.today() - timedelta(days=self.days)

            records = (
                session.query(DailyHealth)
                .filter(DailyHealth.user_id == self.user_id, DailyHealth.date >= cutoff)
                .order_by(DailyHealth.date)
                .all()
            )
            self.health_records = [
                {
                    "date": str(r.date),
                    "resting_hr": r.resting_heart_rate,
                    "hrv_avg": r.hrv_avg,
                    "hrv_status": r.hrv_status,
                    "sleep_score": r.sleep_score,
                    "sleep_hours": round(r.sleep_duration_seconds / 3600, 1) if r.sleep_duration_seconds else None,
                    "deep_sleep_pct": round(r.deep_sleep_seconds / r.sleep_duration_seconds * 100, 1)
                    if r.deep_sleep_seconds and r.sleep_duration_seconds
                    else None,
                    "stress_avg": r.stress_avg,
                    "body_battery_min": r.body_battery_min,
                    "body_battery_max": r.body_battery_max,
                    "steps": r.steps,
                }
                for r in records
            ]

            activities = (
                session.query(Activity)
                .filter(Activity.user_id == self.user_id, Activity.start_time >= cutoff)
                .order_by(Activity.start_time)
                .all()
            )
            self.activities = []
            for a in activities:
                sd = json.loads(a.strength_data) if a.strength_data else None
                exercises: list[dict[str, Any]] = []
                if sd and isinstance(sd, dict):
                    exercises = parse_strength_sets_from_raw(sd)
                if a.activity_type == "strength_training":
                    has_ex = bool(exercises)
                    logger.info(
                        "Strength activity %s (id=%s): strength_data=%s has_exercises=%s",
                        a.start_time.date(), a.activity_id,
                        bool(sd), has_ex,
                    )
                    activity_key = str(a.start_time.date())
                    self._parsed_exercises[activity_key] = exercises
                self.activities.append({
                    "date": str(a.start_time.date()),
                    "type": a.activity_type,
                    "duration_min": round(a.duration_seconds / 60, 1),
                    "distance_km": round(a.distance_meters / 1000, 2) if a.distance_meters else None,
                    "avg_hr": a.avg_heart_rate,
                    "training_effect": a.training_effect,
                    "vo2max": a.vo2max,
                    "strength_data": sd,
                })
        finally:
            session.close()

    def to_summary(self) -> str:
        if self._summary is not None:
            return self._summary
        self._summary = self._build_summary()
        return self._summary

    def _build_summary(self) -> str:
        lines = [f"Health data for user {self.user_id} (last {self.days} days):", ""]

        if self.health_records:
            lines.append("## Daily Health")
            for r in self.health_records[-7:]:
                hr = f"HRV={r['hrv_avg']}" + (f"({r['hrv_status']})" if r['hrv_status'] else "")
                sl = f"sleep={r['sleep_hours']}h(score={r['sleep_score']})"
                bb = f"BB={r['body_battery_min']}-{r['body_battery_max']}"
                lines.append(f"- {r['date']}: {hr}, {sl}, stress={r['stress_avg']}, {bb}")

        if self.activities:
            lines.append("")
            lines.append("## Activities")
            for a in self.activities[-5:]:
                d = f", {a['distance_km']}km" if a['distance_km'] else ""
                lines.append(f"- {a['date']}: {a['type']} {a['duration_min']}min{d}, HR={a['avg_hr']}")
                activity_key = a["date"]
                exercises = self._parsed_exercises.get(activity_key, [])
                for ex in exercises:
                    sets_str = ", ".join(ex["sets"])
                    lines.append(f"  - {ex['name']}: {sets_str}")

        return "\n".join(lines)
