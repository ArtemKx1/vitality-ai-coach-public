from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func

from src.db.database import get_session
from src.db.models import Activity, DailyHealth, Insight
from src.services.firebase import send_push

logger = logging.getLogger(__name__)

HRV_DROP_PCT = 15
SLEEP_HOURS_MIN = 6.0
SLEEP_SCORE_MIN = 60.0
STRESS_HIGH = 50.0
TRAINING_EFFECT_HIGH = 3.0
INACTIVE_DAYS = 3
ALERT_COOLDOWN_H = 24


def _recent_categories(user_id: int, since: datetime) -> set[str]:
    session = get_session()
    try:
        rows = (
            session.query(Insight.category)
            .filter(Insight.user_id == user_id, Insight.created_at >= since)
            .distinct()
            .all()
        )
        return {row[0] for row in rows}
    finally:
        session.close()


def _save_and_send(user_id: int, title: str, body: str, category: str, severity: str = "info"):
    session = get_session()
    try:
        session.add(Insight(
            user_id=user_id,
            date=date.today(),
            category=category,
            title=title,
            content=body,
            severity=severity,
        ))
        session.commit()
    finally:
        session.close()
    send_push(user_id, title, body, data={"category": category})
    logger.info("Alert [%s] for user %s: %s", category, user_id, title)


def check_and_alert(user_id: int) -> list[str]:
    now = datetime.now(timezone.utc)
    cooldown_threshold = now - timedelta(hours=ALERT_COOLDOWN_H)
    recent = _recent_categories(user_id, cooldown_threshold)

    session = get_session()
    try:
        records = (
            session.query(DailyHealth)
            .filter(DailyHealth.user_id == user_id)
            .order_by(DailyHealth.date.desc())
            .limit(2)
            .all()
        )
        if len(records) < 2:
            return []

        activities = (
            session.query(Activity)
            .filter(Activity.user_id == user_id)
            .order_by(Activity.start_time.desc())
            .limit(3)
            .all()
        )
    finally:
        session.close()

    latest = records[0]
    baseline = records[1:] if len(records) > 1 else []

    def _avg_hrv() -> float | None:
        vals = [r.hrv_avg for r in baseline if r.hrv_avg is not None]
        return sum(vals) / len(vals) if vals else None

    triggered: list[str] = []

    # HRV drop
    if "hrv_drop" not in recent:
        avg_hrv = _avg_hrv()
        cur_hrv = latest.hrv_avg
        if avg_hrv and cur_hrv and avg_hrv > 0:
            drop_pct = (avg_hrv - cur_hrv) / avg_hrv * 100
            if drop_pct >= HRV_DROP_PCT:
                _save_and_send(
                    user_id,
                    "HRV dropped significantly",
                    f"Your HRV dropped {drop_pct:.0f}% (from {avg_hrv:.0f} \u2192 {cur_hrv:.0f} ms). "
                    "This may indicate stress, poor sleep, or overtraining.",
                    category="hrv_drop",
                    severity="warning",
                )
                triggered.append("hrv_drop")

    # Low sleep
    if "low_sleep" not in recent:
        sleep_h = latest.sleep_duration_seconds / 3600 if latest.sleep_duration_seconds else None
        if sleep_h is not None and sleep_h < SLEEP_HOURS_MIN:
            _save_and_send(
                user_id,
                "Low sleep detected",
                f"You only slept {sleep_h:.1f}h last night (recommended: 7-9h). "
                "Prioritize recovery tonight.",
                category="low_sleep",
                severity="warning",
            )
            triggered.append("low_sleep")

    # Poor sleep score
    if "poor_sleep" not in recent:
        score = latest.sleep_score
        if score is not None and score < SLEEP_SCORE_MIN:
            _save_and_send(
                user_id,
                "Poor sleep quality",
                f"Your sleep score was {score:.0f}/100. Consider adjusting your sleep habits.",
                category="poor_sleep",
                severity="warning",
            )
            triggered.append("poor_sleep")

    # High stress
    if "high_stress" not in recent:
        stress = latest.stress_avg
        if stress is not None and stress > STRESS_HIGH:
            _save_and_send(
                user_id,
                "Elevated stress detected",
                f"Your average stress today was {stress:.0f} (above normal). "
                "Try breathing exercises or light activity.",
                category="high_stress",
                severity="warning",
            )
            triggered.append("high_stress")

    # Hard session
    if "hard_session" not in recent and activities:
        latest_act = activities[0]
        te = latest_act.training_effect
        if te is not None and te >= TRAINING_EFFECT_HIGH:
            _save_and_send(
                user_id,
                f"Hard {latest_act.activity_type} session detected",
                f"Training effect {te:.1f} ({latest_act.duration_seconds / 60:.0f} min). "
                "Make sure to recover properly.",
                category="hard_session",
                severity="info",
            )
            triggered.append("hard_session")

    # Inactive streak
    if "inactive_streak" not in recent:
        if activities:
            last_act = activities[0]
            days_inactive = (date.today() - last_act.start_time.date()).days
            if days_inactive >= INACTIVE_DAYS:
                _save_and_send(
                    user_id,
                    "No activity recently",
                    f"Your last recorded activity was {days_inactive} days ago. "
                    "A light session can help maintain your fitness.",
                    category="inactive_streak",
                    severity="info",
                )
                triggered.append("inactive_streak")
        else:
            _save_and_send(
                user_id,
                "No activity data yet",
                "We haven't recorded any activities. Start a workout to get personalized insights!",
                category="inactive_streak",
                severity="info",
            )
            triggered.append("inactive_streak")

    return triggered
