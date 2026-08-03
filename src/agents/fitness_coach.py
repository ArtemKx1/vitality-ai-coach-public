from __future__ import annotations

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.services.context import HealthContext

logger = logging.getLogger(__name__)

FITNESS_COACH_PROMPT = """You are an expert athletic coach with deep knowledge of exercise physiology, covering both endurance and strength training.
Based on the athlete's Garmin training and health data below, provide coaching insights.

Focus on:
1. Training load — is ATL/CTL balanced? Risk of overtraining? For strength sessions: volume, intensity, and progression
2. Recovery status — HRV, sleep, and stress implications for today's workout
3. Workout recommendations — running, strength, or mixed: what type, intensity, and duration for today
4. Strength-specific analysis — exercise selection, set/rep schemes, weight progression, muscle group balance
5. Long-term trends — fitness improving, plateau, or declining? Strength PRs or volume milestones
6. Injury prevention signals — spikes in load, poor recovery, form degradation

Data:
{data}

Return 2-5 coaching insights as a raw JSON array (no markdown, no code fences). Each object:
- category: "training_load" | "recovery" | "workout" | "long_term" | "injury_prevention"
- title: short title
- content: detailed coaching advice with specific numbers
- severity: "info" | "warning" | "alert"
"""


class FitnessCoachAgent(BaseAgent):
    name = "fitness_coach"

    def __init__(self, llm):
        self._llm = llm

    def analyze(self, ctx: HealthContext) -> list[dict[str, Any]]:
        summary = ctx.to_summary()
        prompt = FITNESS_COACH_PROMPT.format(data=summary)

        try:
            response = self._llm.invoke(prompt)
            return self._parse(response)
        except Exception as e:
            logger.error("Fitness coach failed: %s", e)
            return [{"category": "recovery", "title": "Coaching unavailable", "content": "Unable to generate coaching advice. Please try again later.", "severity": "info"}]

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
        return [{"category": "general", "title": "Coach says", "content": content, "severity": "info"}]
