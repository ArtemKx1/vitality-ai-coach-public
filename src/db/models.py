from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.config import settings

_db_path = Path(settings.database_url.replace("sqlite:///", "")).parent
_db_path.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, echo=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    garmin_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    garmin_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    garmin_connected: Mapped[bool] = mapped_column(default=False)
    garmin_tokens: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    goal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activities: Mapped[str | None] = mapped_column(Text, nullable=True)
    fitness_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(default=False)


class DailyHealth(Base):
    __tablename__ = "daily_health"
    __table_args__ = (
        Index("ix_daily_health_user_id", "user_id"),
        Index("ix_daily_health_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column()
    resting_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    hrv_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sleep_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    deep_sleep_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_sleep_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    rem_sleep_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    awake_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_battery_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_battery_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiration_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_id", name="uq_activity_per_user"),
        Index("ix_activities_user_id", "user_id"),
        Index("ix_activities_user_start", "user_id", "start_time"),
        Index("ix_activities_strength_backfill", "user_id", "activity_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    activity_id: Mapped[str] = mapped_column(String(100))
    activity_type: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    duration_seconds: Mapped[float] = mapped_column(Float)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pace_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    training_effect: Mapped[float | None] = mapped_column(Float, nullable=True)
    anaerobic_effect: Mapped[float | None] = mapped_column(Float, nullable=True)
    vo2max: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_power: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_cadence: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    strength_data: Mapped[str | None] = mapped_column(Text, nullable=True)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (Index("ix_devices_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    device_id: Mapped[int] = mapped_column(BigInteger)
    display_name: Mapped[str] = mapped_column(String(255))
    type_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (Index("ix_chat_conversations_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), default="New Chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_conversation_id", "conversation_id"),
        Index("ix_chat_messages_conv_created", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("chat_conversations.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (Index("ix_device_tokens_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(512), unique=True)
    platform: Mapped[str] = mapped_column(String(20), default="android")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (Index("ix_insights_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column()
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(engine)
    from sqlalchemy import inspect, text
    with engine.connect() as conn:
        inspector = inspect(conn)
        for table, cols in [
            ("users", [
                ("goal", "VARCHAR(50)"),
                ("primary_activity", "VARCHAR(50)"),
                ("activities", "TEXT"),
                ("fitness_level", "VARCHAR(50)"),
                ("equipment", "VARCHAR(50)"),
                ("onboarding_completed", "BOOLEAN DEFAULT FALSE"),
                ("garmin_tokens", "TEXT"),
            ]),
            ("activities", [
                ("device_id", "INTEGER"),
                ("strength_data", "TEXT"),
            ]),
        ]:
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col_name, col_type in cols:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))
        conn.commit()

    # Create indexes that may not exist yet (safe: IF NOT EXISTS)
    with engine.connect() as conn:
        for ddl in [
            "CREATE INDEX IF NOT EXISTS ix_daily_health_user_id ON daily_health (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_daily_health_user_date ON daily_health (user_id, date)",
            "CREATE INDEX IF NOT EXISTS ix_activities_user_id ON activities (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_activities_user_start ON activities (user_id, start_time)",
            "CREATE INDEX IF NOT EXISTS ix_activities_strength_backfill ON activities (user_id, activity_type)",
            "CREATE INDEX IF NOT EXISTS ix_devices_user_id ON devices (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_chat_conversations_user_id ON chat_conversations (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages (conversation_id)",
            "CREATE INDEX IF NOT EXISTS ix_chat_messages_conv_created ON chat_messages (conversation_id, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_device_tokens_user_id ON device_tokens (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_insights_user_id ON insights (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_insights_user_cat_created ON insights (user_id, category, created_at)",
            "CREATE INDEX IF NOT EXISTS ix_insights_user_created ON insights (user_id, created_at)",
        ]:
            conn.execute(text(ddl))
        conn.commit()
