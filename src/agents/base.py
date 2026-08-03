from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.services.context import HealthContext


class BaseAgent(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, ctx: HealthContext) -> list[dict[str, Any]]: ...
