"""Unit tests for the shared schemas (Step C2)."""

from datetime import date
from pathlib import Path
import sys

import pytest
from pydantic import BaseModel, ValidationError

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import calendar_ics, schemas

EXERCISE = {"name": "Squat", "activity_type": "strength", "sets": 3, "reps": 10}
SESSION = {
    "start": "2026-11-24T07:00:00",
    "end": "2026-11-24T08:00:00",
    "focus": "legs",
    "exercises": [EXERCISE],
}
LOG = {"date": "2026-11-24", "exercise": "Squat", "sets": 3, "reps": 10}


def test_empty_profile_is_valid_and_lists_are_not_shared() -> None:
    first, second = schemas.UserProfile(), schemas.UserProfile()
    first.goals.append("strength")
    assert second.goals == []
    assert second.height_cm is None


@pytest.mark.parametrize(
    "field, accepted, rejected",
    [
        ("height_cm", [100.1, 249.9], [100, 250]),
        ("weight_kg", [30.1, 299.9], [30, 300]),
        ("workout_days", [1, 6], [0, 7]),
        ("session_minutes", [15, 120], [14, 121]),
        ("experience", ["beginner", "intermediate", "advanced"], ["expert"]),
    ],
)
def test_profile_limits(field: str, accepted: list, rejected: list) -> None:
    for value in accepted:
        assert getattr(schemas.UserProfile(**{field: value}), field) == value
    for value in rejected:
        with pytest.raises(ValidationError):
            schemas.UserProfile(**{field: value})


def test_chat_response_defaults_to_not_refused() -> None:
    response = schemas.ProfileChatResponse(
        reply="Hi", profile=schemas.UserProfile(), missing_fields=["goals"]
    )
    assert response.refused is False


def test_plan_round_trips_through_json() -> None:
    plan = schemas.WeeklyPlan(week_of="2026-11-23", sessions=[SESSION])
    assert plan.week_of == date(2026, 11, 23)
    assert schemas.WeeklyPlan.model_validate_json(plan.model_dump_json()) == plan


@pytest.mark.parametrize(
    "model, valid, change",
    [
        (schemas.Exercise, EXERCISE, {"activity_type": "dance"}),
        (schemas.Exercise, EXERCISE, {"sets": 0}),
        (schemas.Exercise, EXERCISE, {"sets": 7}),
        (schemas.Exercise, EXERCISE, {"reps": 0}),
        (schemas.Exercise, EXERCISE, {"reps": 31}),
        (schemas.Session, SESSION, {"exercises": []}),
        (schemas.LogEntry, LOG, {"sets": 0}),
        (schemas.LogEntry, LOG, {"reps": 0}),
        (schemas.LogEntry, LOG, {"weight_kg": -1}),
        (schemas.LogEntry, LOG, {"date": "not a date"}),
    ],
)
def test_bad_values_are_rejected(
    model: type[BaseModel], valid: dict, change: dict
) -> None:
    model(**valid)  # proves only the changed value causes the failure
    with pytest.raises(ValidationError):
        model(**(valid | change))


def test_dates_are_parsed() -> None:
    assert schemas.LogEntry(**LOG).date == date(2026, 11, 24)
    best = schemas.PersonalBest(exercise="Squat", best_weight_kg=80, date="2026-11-24")
    assert best.date == date(2026, 11, 24)


def test_calendar_uses_shared_free_slot() -> None:
    assert calendar_ics.FreeSlot is schemas.FreeSlot


@pytest.mark.parametrize(
    "model, valid, change",
    [
        (schemas.Exercise, EXERCISE, {"sets": 1, "reps": 1}),
        (schemas.Exercise, EXERCISE, {"sets": 6, "reps": 30}),
        (schemas.LogEntry, LOG, {"sets": 1, "reps": 1, "weight_kg": 0}),
    ],
)
def test_boundary_values_are_accepted(
    model: type[BaseModel], valid: dict, change: dict
) -> None:
    model(**(valid | change))


@pytest.mark.parametrize(
    "model, required",
    [
        (schemas.UserProfile, set()),
        (schemas.ProfileChatResponse, {"reply", "profile", "missing_fields"}),
        (schemas.FreeSlot, {"start", "end"}),
        (schemas.Exercise, {"name", "activity_type", "sets", "reps"}),
        (schemas.Session, {"start", "end", "focus", "exercises"}),
        (schemas.WeeklyPlan, {"week_of", "sessions"}),
        (schemas.LogEntry, {"date", "exercise", "sets", "reps"}),
        (schemas.PersonalBest, {"exercise", "best_weight_kg", "date"}),
    ],
)
def test_exactly_these_fields_are_required(
    model: type[BaseModel], required: set[str]
) -> None:
    fields = model.model_fields.items()
    assert {name for name, field in fields if field.is_required()} == required


@pytest.mark.parametrize("activity", ["strength", "cardio", "mobility"])
def test_activity_types_are_accepted(activity: str) -> None:
    exercise = schemas.Exercise(**(EXERCISE | {"activity_type": activity}))
    assert exercise.activity_type == activity
