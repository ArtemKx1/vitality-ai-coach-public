from __future__ import annotations

from sqlalchemy.orm import Session

from src.db.models import engine


def get_session() -> Session:
    return Session(engine)
