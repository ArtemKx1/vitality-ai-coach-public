from __future__ import annotations

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.services.context import HealthContext

logger = logging.getLogger(__name__)

HEALTH_ANALYST_PROMPT = """You are a health data analyst specializing in wearable metrics.
Analyze the user's Garmin health data below and produce insights.

Focus on:
1. HRV trends — is it stable, dropping, improving? What might explain changes?
2. Sleep quality — duration, deep sleep %, consistency. Any patterns?
3. Stress & recovery — correlation between stress, HRV, and sleep
4. Body Battery — charge/discharge patterns, recovery rate
5. Resting HR — any upward/downward trends
6. Correlations between metrics — e.g. "HRV drops day after poor sleep"

Data:
{data}

Return 2-5 specific, actionable insights as a raw JSON array (no markdown, no code fences). Each object:
- category: "hrv" | "sleep" | "stress" | "recovery" | "general"
- title: short title
- content: detailed explanation with specific numbers
- severity: "info" | "warning" | "alert"
"""


class HealthAnalystAgent(BaseAgent):
    name = "health_analyst"

    def __init__(self, llm):
        self._llm = llm

    def analyze(self, ctx: HealthContext) -> list[dict[str, Any]]:
        summary = ctx.to_summary()
        prompt = HEALTH_ANALYST_PROMPT.format(data=summary)

        try:
            response = self._llm.invoke(prompt)
            return self._parse(response)
        except Exception as e:
            logger.error("Health analyst failed: %s", e)
            return [{"category": "general", "title": "Analysis unavailable", "content": "Unable to complete analysis. Please try again later.", "severity": "info"}]

    def _parse(self, response: Any) -> list[dict[str, Any]]:
        content = response.content if hasattr(response, "content") else str(response)
        import json as _json
        maybe = content.strip()
        if maybe.startswith("```"):
            maybe = maybe.split("\n", 1)[-1].rsplit("\n", 1)[0] if "\n" in maybe else maybe.replace("```json", "").replace("```", "")
        try:
            parsed = _json.loads(maybe)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [{"category": "general", "title": "Analysis", "content": content, "severity": "info"}]
