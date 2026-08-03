from __future__ import annotations

from datetime import date

from src.db.database import get_session
from src.db.models import Insight
from src.security import decrypt, encrypt

def _safe_decrypt(text: str) -> str:
    try:
        return decrypt(text)
    except Exception:
        return text


class InsightsService:
    def save_insight(self, user_id: int, category: str, title: str, content: str, severity: str = "info") -> None:
        session = get_session()
        try:
            record = Insight(
                user_id=user_id,
                date=date.today(),
                category=category,
                title=encrypt(title),
                content=encrypt(content),
                severity=severity,
            )
            session.add(record)
            session.commit()
        finally:
            session.close()

    def get_recent(self, user_id: int, limit: int = 20) -> list[dict]:
        session = get_session()
        try:
            records = (
                session.query(Insight)
                .filter(Insight.user_id == user_id)
                .order_by(Insight.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": r.id,
                    "date": str(r.date),
                    "category": r.category,
                    "title": _safe_decrypt(r.title),
                    "content": _safe_decrypt(r.content),
                    "severity": r.severity,
                }
                for r in records
            ]
        finally:
            session.close()
