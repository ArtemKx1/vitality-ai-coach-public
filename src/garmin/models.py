from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class GarminCredentials(BaseModel):
    email: str
    password: str


class DailyHealthData(BaseModel):
    date: date
    resting_heart_rate: float | None = None
    hrv_avg: float | None = None
    hrv_status: str | None = None
    sleep_score: float | None = None
    sleep_duration_seconds: float | None = None
    deep_sleep_seconds: float | None = None
    light_sleep_seconds: float | None = None
    rem_sleep_seconds: float | None = None
    awake_seconds: float | None = None
    stress_avg: float | None = None
    body_battery_min: float | None = None
    body_battery_max: float | None = None
    steps: int | None = None
    total_calories: float | None = None
    spo2_avg: float | None = None
    respiration_avg: float | None = None
    raw_data: dict[str, Any] | None = None


class DeviceData(BaseModel):
    device_id: int
    product_display_name: str
    device_type_simple_name: str | None = None
    application_key: str | None = None


class ActivityData(BaseModel):
    activity_id: str
    activity_type: str
    start_time: datetime
    duration_seconds: float
    distance_meters: float | None = None
    device_id: int | None = None
    avg_heart_rate: float | None = None
    max_heart_rate: float | None = None
    avg_pace_km: float | None = None
    elevation_gain: float | None = None
    training_effect: float | None = None
    anaerobic_effect: float | None = None
    vo2max: float | None = None
    calories: float | None = None
    avg_power: float | None = None
    avg_cadence: float | None = None
    raw_data: dict[str, Any] | None = None
    strength_sets_raw: dict[str, Any] | None = None


class ExerciseSet(BaseModel):
    set_number: int
    reps: int | None = None
    weight_kg: float | None = None
    duration_seconds: float | None = None


class StrengthExercise(BaseModel):
    category: str | None
    name: str | None
    sets: list[ExerciseSet] = []


class StrengthWorkoutData(BaseModel):
    exercises: list[StrengthExercise] = []
    total_sets: int | None = None
    total_reps: int | None = None
    total_volume: float | None = None


def parse_strength_sets_from_raw(raw: dict[str, Any] | list | None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    if not isinstance(raw, dict):
        return results
    exercise_sets = raw.get("exerciseSets") or raw.get("data", {}).get("exerciseSets") or []
    sets_by_exercise: dict[str, list[str]] = {}
    for entry in exercise_sets:
        if not isinstance(entry, dict):
            continue
        if entry.get("setType") != "ACTIVE":
            continue
        ex_list = entry.get("exercises", [])
        if not ex_list or not isinstance(ex_list[0], dict):
            continue
        ex = ex_list[0]
        cat = ex.get("category") or ""
        name = ex.get("name") or ""
        label = f"{cat}/{name}" if cat and name else (cat or name)
        if not label:
            continue

        parts = []
        reps = entry.get("repetitionCount")
        if reps:
            parts.append(f"{reps} reps")
        weight_grams = entry.get("weight")
        if weight_grams:
            kg = weight_grams / 1000
            parts.append(f"{kg:.1f} kg")
        duration = entry.get("duration")
        if duration:
            parts.append(f"{duration:.0f}s")

        if parts:
            sets_by_exercise.setdefault(label, []).append(", ".join(parts))

    for name, sets in sets_by_exercise.items():
        results.append({"name": name, "sets": sets})
    return results
