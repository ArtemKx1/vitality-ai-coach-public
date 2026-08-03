from __future__ import annotations

from datetime import date

from src.db.models import DailyHealth, User, init_db


def test_init_db():
    init_db()


def test_user_model():
    u = User(garmin_email="test@example.com")
    assert u.garmin_email == "test@example.com"


def test_daily_health_model():
    h = DailyHealth(
        user_id=1,
        date=date.today(),
        resting_heart_rate=58.0,
        hrv_avg=42.5,
        sleep_score=85.0,
        steps=10000,
    )
    assert h.resting_heart_rate == 58.0
    assert h.hrv_avg == 42.5
    assert h.steps == 10000
