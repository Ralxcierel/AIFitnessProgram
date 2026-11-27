"""Unit tests for the eval scoring in eval/metrics.py (Step C4).

Pure Python; nothing here calls the API or touches the database.
"""

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any

import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas import FreeSlot
from eval import metrics

PROFILE_CASE: dict[str, Any] = {
    "id": "profile-x",
    "expect": {
        "refused": False,
        "exact": {"experience": "beginner", "workout_days": 3},
        "approx": {"height_cm": {"value": 172, "tolerance": 1}},
        "contains": {"goals": [["strength", "stronger"], ["run"]]},
        "empty": ["injuries", "health_notes"],
        "missing_fields": ["weight_kg", "session_minutes"],
    },
}
GOOD_PROFILE = {
    "height_cm": 172.5,
    "experience": "beginner",
    "goals": ["Get STRONGER", "run a 5k"],
    "workout_days": 3,
}


def chat_body(profile: dict[str, Any], **extra: Any) -> dict[str, Any]:
    body = {
        "reply": "ok",
        "profile": profile,
        "missing_fields": ["weight_kg", "session_minutes"],
        "refused": False,
    }
    body.update(extra)
    return body


def failed(score: metrics.CaseScore) -> list[str]:
    return [name for name, ok in score.checks if not ok]


# --- profile ---


def test_profile_all_checks_pass() -> None:
    score = metrics.score_profile(PROFILE_CASE, 200, chat_body(GOOD_PROFILE))
    assert score.schema_valid
    assert failed(score) == []
    assert score.total == 1 + 2 + 1 + 2 + 2 + 1


def test_profile_check_names_match_the_scored_checks() -> None:
    score = metrics.score_profile(PROFILE_CASE, 200, chat_body(GOOD_PROFILE))
    assert [name for name, _ in score.checks] == metrics.profile_check_names(
        PROFILE_CASE["expect"]
    )


@pytest.mark.parametrize(
    ("change", "fails"),
    [
        ({"experience": "advanced"}, ["exact:experience"]),
        ({"workout_days": None}, ["exact:workout_days"]),
        ({"height_cm": 174}, ["approx:height_cm"]),
        ({"height_cm": None}, ["approx:height_cm"]),
        ({"goals": ["run a 5k"]}, ["contains:goals:1"]),
        ({"goals": []}, ["contains:goals:1", "contains:goals:2"]),
        ({"injuries": ["sore back"]}, ["empty:injuries"]),
        ({"health_notes": "asthma"}, ["empty:health_notes"]),
    ],
)
def test_profile_single_field_failures(change: dict[str, Any], fails: list[str]) -> None:
    score = metrics.score_profile(PROFILE_CASE, 200, chat_body({**GOOD_PROFILE, **change}))
    assert failed(score) == fails


def test_profile_tolerance_edge_passes() -> None:
    score = metrics.score_profile(
        PROFILE_CASE, 200, chat_body({**GOOD_PROFILE, "height_cm": 173})
    )
    assert failed(score) == []


def test_profile_refused_and_missing_fields_are_checked() -> None:
    body = chat_body(GOOD_PROFILE, refused=True, missing_fields=[])
    assert failed(metrics.score_profile(PROFILE_CASE, 200, body)) == [
        "refused",
        "missing_fields",
    ]


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, {"reply": "ok"}),  # not a ProfileChatResponse
        (200, chat_body({"workout_days": 7})),  # outside the schema's range
        (502, {"error": "The model call failed", "detail": "x"}),
        (None, None),
    ],
)
def test_profile_invalid_answer_fails_every_check(status: int | None, body: Any) -> None:
    score = metrics.score_profile(PROFILE_CASE, status, body)
    assert not score.schema_valid
    assert score.passed == 0
    assert score.total == len(metrics.profile_check_names(PROFILE_CASE["expect"]))


# --- plan ---

SLOTS = [
    FreeSlot(start=datetime(2026, 11, 23 + d, 6), end=datetime(2026, 11, 23 + d, 9))
    for d in range(7)
]
PLAN_CASE: dict[str, Any] = {
    "id": "plan-x",
    "saved_profile": {
        "height_cm": 170,
        "weight_kg": 70,
        "experience": "beginner",
        "goals": ["fit"],
        "workout_days": 2,
        "session_minutes": 45,
    },
    "expect": {
        "status": 200,
        "passes_checks": True,
        "session_count": 2,
        "notes_contain": [["doctor", "physical therapist"]],
        "detail_contains": [],
        "exercises_exclude": ["barbell"],
    },
}
REFUSAL_CASE: dict[str, Any] = {
    "id": "plan-r",
    "saved_profile": PLAN_CASE["saved_profile"],
    "expect": {
        "status": 400,
        "passes_checks": None,
        "session_count": None,
        "notes_contain": [],
        "detail_contains": [["free time on only 1"], ["3 workouts"]],
        "exercises_exclude": [],
    },
}


def session(day: int, name: str = "Goblet squat", start: datetime | None = None) -> dict:
    begin = start or datetime(2026, 11, 23 + day, 6)
    return {
        "start": begin.isoformat(),
        "end": (begin + timedelta(minutes=45)).isoformat(),
        "focus": "Full body",
        "exercises": [{"name": name, "activity_type": "strength", "sets": 3, "reps": 10}],
    }


def plan_body(*sessions: dict, notes: list[str] | None = None) -> dict:
    return {
        "week_of": "2026-11-23",
        "sessions": list(sessions),
        "notes": ["Ask a doctor first."] if notes is None else notes,
    }


def test_plan_all_checks_pass() -> None:
    score = metrics.score_plan(PLAN_CASE, 200, plan_body(session(0), session(2)), SLOTS)
    assert score.schema_valid and score.constraint_pass
    assert failed(score) == []
    assert [n for n, _ in score.checks] == metrics.plan_check_names(PLAN_CASE["expect"])


def test_plan_rule_problem_fails_passes_checks_and_constraint() -> None:
    late = session(2, start=datetime(2026, 11, 25, 12))  # outside the 06-09 slot
    score = metrics.score_plan(PLAN_CASE, 200, plan_body(session(0), late), SLOTS)
    assert score.constraint_pass is False
    assert failed(score) == ["passes_checks"]
    assert score.problems and "not fully inside one free time slot" in score.problems[0]


def test_plan_judgement_checks() -> None:
    body = plan_body(session(0, "Barbell back squat"), session(2), notes=[])
    score = metrics.score_plan(PLAN_CASE, 200, body, SLOTS)
    assert failed(score) == ["notes_contain:1", "exercises_exclude"]
    assert score.constraint_pass  # judgement checks do not affect it


def test_plan_wrong_session_count() -> None:
    score = metrics.score_plan(PLAN_CASE, 200, plan_body(session(0)), SLOTS)
    assert "session_count" in failed(score)


def test_plan_times_with_a_time_zone_are_made_local_first() -> None:
    local = datetime(2026, 11, 23, 6)
    aware = local.astimezone().astimezone(timezone.utc)
    score = metrics.score_plan(
        PLAN_CASE, 200, plan_body(session(0, start=aware), session(2)), SLOTS
    )
    assert score.constraint_pass, score.problems


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (502, {"error": "The plan did not pass the checks", "detail": "x"}),
        (400, {"error": "Request refused", "detail": "x"}),
        (200, {"sessions": "nope"}),
        (None, None),
    ],
)
def test_plan_bad_answer_fails_all_but_a_matching_status(status: Any, body: Any) -> None:
    score = metrics.score_plan(PLAN_CASE, status, body, SLOTS)
    assert not score.schema_valid
    assert score.constraint_pass is False
    expected_passed = 1 if status == 200 else 0
    assert score.passed == expected_passed


def test_plan_check_crash_counts_as_a_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args: Any) -> list[str]:
        raise TypeError("cannot compare")

    monkeypatch.setattr(metrics, "check_plan", boom)
    score = metrics.score_plan(PLAN_CASE, 200, plan_body(session(0), session(2)), SLOTS)
    assert score.constraint_pass is False
    assert score.problems == ["The checks could not run (TypeError)."]


def test_refusal_case_passes_with_status_and_detail() -> None:
    body = {
        "error": "Request refused",
        "detail": "Your calendar has free time on only 1 days this week, "
        "but your profile asks for 3 workouts.",
    }
    score = metrics.score_plan(REFUSAL_CASE, 400, body, SLOTS)
    assert failed(score) == []
    assert score.constraint_pass is None
    assert score.schema_valid is False  # a refusal has no plan to validate
    assert score.total == 3


def test_refusal_case_fails_when_a_plan_comes_back() -> None:
    score = metrics.score_plan(REFUSAL_CASE, 200, plan_body(session(0)), SLOTS)
    assert score.passed == 0
    assert score.constraint_pass is None


# --- summary ---


def test_summary_rates() -> None:
    profile_ok = metrics.score_profile(PROFILE_CASE, 200, chat_body(GOOD_PROFILE))
    profile_bad = metrics.score_profile(PROFILE_CASE, 502, None)
    plan_ok = metrics.score_plan(PLAN_CASE, 200, plan_body(session(0), session(2)), SLOTS)
    plan_bad = metrics.score_plan(PLAN_CASE, 502, None, SLOTS)
    refusal = metrics.score_plan(REFUSAL_CASE, 400, {"detail": "free time on only 1, 3 workouts"}, SLOTS)
    summary = metrics.summarize([profile_ok, profile_bad, plan_ok, plan_bad, refusal])
    assert summary["profile"]["schema_valid_rate"] == 0.5
    assert summary["profile"]["check_pass_rate"] == 0.5
    assert summary["plan"]["constraint_pass_rate"] == 0.5
    assert summary["plan"]["constraint_cases"] == 2
    assert summary["plan"]["checks_total"] == 5 + 5 + 3
    assert json.dumps(summary)  # report-ready


def test_summary_of_nothing_is_empty() -> None:
    assert metrics.summarize([]) == {}
