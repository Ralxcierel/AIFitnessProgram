"""Unit tests for the weekly plan rule checks (Step B3).

Plain Python only; nothing here calls the API or touches the database.
"""

from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sys

import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import plan_checks
from backend.app.plan_checks import check_plan
from backend.app.schemas import Exercise, FreeSlot, Session, UserProfile, WeeklyPlan

MONDAY = date(2026, 11, 23)
PROFILE = UserProfile(workout_days=3, session_minutes=45)
# One free slot from 06:00 to 09:00 on each of the seven days.
SLOTS = [
    FreeSlot(
        start=datetime(2026, 11, 23 + day, 6), end=datetime(2026, 11, 23 + day, 9)
    )
    for day in range(7)
]
GOOD = Exercise(name="Goblet squat", activity_type="strength", sets=3, reps=10)


def session(
    day: int,
    hour: int = 6,
    minute: int = 0,
    minutes: int = 45,
    exercises: list[Exercise] | None = None,
) -> Session:
    start = datetime(2026, 11, 23 + day, hour, minute)
    return Session(
        start=start,
        end=start + timedelta(minutes=minutes),
        focus="Full body",
        exercises=exercises or [GOOD],
    )


def week(*sessions: Session) -> WeeklyPlan:
    return WeeklyPlan(week_of=MONDAY, sessions=list(sessions))


def good_plan() -> WeeklyPlan:
    return week(session(0), session(2), session(4))


def test_good_plan_passes() -> None:
    assert check_plan(good_plan(), PROFILE, SLOTS) == []


# --- number of sessions and rest days ---


def test_too_few_sessions() -> None:
    problems = check_plan(week(session(0), session(2)), PROFILE, SLOTS)
    assert problems == ["The plan has 2 sessions, but the profile asks for 3."]


def test_too_many_sessions() -> None:
    plan = week(*(session(day) for day in range(4)))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert problems == ["The plan has 4 sessions, but the profile asks for 3."]


def test_more_than_six_sessions_and_no_rest_day() -> None:
    plan = week(*(session(day) for day in range(7)))
    profile = PROFILE.model_copy(update={"workout_days": 6})
    problems = check_plan(plan, profile, SLOTS)
    assert "The plan has 7 sessions, but the profile asks for 6." in problems
    assert "The plan has 7 sessions; the most allowed is 6." in problems
    assert "The plan has no rest day." in problems


def test_six_sessions_on_six_days_pass() -> None:
    plan = week(*(session(day) for day in range(6)))
    profile = PROFILE.model_copy(update={"workout_days": 6})
    assert check_plan(plan, profile, SLOTS) == []


def test_two_sessions_on_one_day() -> None:
    plan = week(session(0), session(0, hour=7, minute=30), session(4))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert problems == [
        "Session 2 (Mon 23 Nov 07:30) is on a day that already has a session."
    ]


# --- times ---


def test_session_longer_than_session_minutes() -> None:
    plan = week(session(0, minutes=60), session(2), session(4))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert problems == [
        "Session 1 (Mon 23 Nov 06:00) is 60 minutes long; the most allowed is 45."
    ]


def test_session_shorter_than_15_minutes() -> None:
    plan = week(session(0, minutes=10), session(2), session(4))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert problems == [
        "Session 1 (Mon 23 Nov 06:00) is 10 minutes long; the shortest allowed is 15."
    ]


def test_session_of_exactly_15_minutes_passes() -> None:
    plan = week(session(0, minutes=15), session(2), session(4))
    assert check_plan(plan, PROFILE, SLOTS) == []


def test_session_of_exactly_session_minutes_passes() -> None:
    plan = week(session(0, minutes=45), session(2), session(4))
    assert check_plan(plan, PROFILE, SLOTS) == []


def test_session_that_ends_before_it_starts() -> None:
    backwards = session(0).model_copy(update={"end": datetime(2026, 11, 23, 5)})
    problems = check_plan(week(backwards, session(2), session(4)), PROFILE, SLOTS)
    assert problems == ["Session 1 (Mon 23 Nov 06:00) does not end after it starts."]


@pytest.mark.parametrize(
    ("hour", "minute"),
    [(5, 30), (8, 30), (12, 0)],  # starts early, runs past the end, wholly outside
)
def test_session_outside_a_free_slot(hour: int, minute: int) -> None:
    plan = week(session(0, hour=hour, minute=minute), session(2), session(4))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert len(problems) == 1
    assert problems[0].endswith("is not fully inside one free time slot.")


def test_session_spanning_two_touching_slots_fails() -> None:
    slots = [
        FreeSlot(start=datetime(2026, 11, 23, 6), end=datetime(2026, 11, 23, 7)),
        FreeSlot(start=datetime(2026, 11, 23, 7), end=datetime(2026, 11, 23, 8)),
        *SLOTS[1:],
    ]
    plan = week(session(0, hour=6, minute=30), session(2), session(4))
    problems = check_plan(plan, PROFILE, slots)
    assert problems[0].endswith("is not fully inside one free time slot.")


def test_session_filling_a_slot_exactly_passes() -> None:
    slots = [
        FreeSlot(start=datetime(2026, 11, 23, 6), end=datetime(2026, 11, 23, 6, 45)),
        *SLOTS[1:],
    ]
    assert check_plan(good_plan(), PROFILE, slots) == []


# --- exercises ---


def test_exercise_not_on_the_list() -> None:
    odd = Exercise(name="Kettlebell juggling", activity_type="strength", sets=3, reps=5)
    plan = week(session(0, exercises=[GOOD, odd]), session(2), session(4))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert problems == [
        'Session 1 (Mon 23 Nov 06:00): "Kettlebell juggling" is not on the exercise list.'
    ]


def test_exercise_names_ignore_case_and_extra_spaces() -> None:
    messy = Exercise(name="  goblet   SQUAT ", activity_type="strength", sets=3, reps=10)
    plan = week(session(0, exercises=[messy]), session(2), session(4))
    assert check_plan(plan, PROFILE, SLOTS) == []


def test_exercise_with_the_wrong_activity_type() -> None:
    walk = Exercise(name="Brisk walk", activity_type="strength", sets=1, reps=20)
    plan = week(session(0, exercises=[walk]), session(2), session(4))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert problems == [
        'Session 1 (Mon 23 Nov 06:00): "Brisk walk" is cardio, not strength.'
    ]


def test_long_unknown_name_is_cut_in_the_problem() -> None:
    odd = Exercise(name="x" * 500, activity_type="cardio", sets=1, reps=1)
    plan = week(session(0, exercises=[odd]), session(2), session(4))
    [problem] = check_plan(plan, PROFILE, SLOTS)
    assert "x" * 60 in problem and "x" * 61 not in problem


def test_problems_from_several_rules_are_all_listed() -> None:
    odd = Exercise(name="Moon jump", activity_type="cardio", sets=1, reps=1)
    plan = week(session(0, minutes=60, exercises=[odd]), session(0, hour=12))
    problems = check_plan(plan, PROFILE, SLOTS)
    assert len(problems) == 5  # count, length, unknown name, same day, outside slot


# --- the allow-list file ---


def test_exercise_list_is_well_formed() -> None:
    entries = json.loads(plan_checks.EXERCISES_FILE.read_text(encoding="utf-8"))
    assert len(entries) >= 30
    names = [plan_checks.normalize(entry["name"]) for entry in entries]
    assert len(names) == len(set(names)), "duplicate exercise names"
    types = {entry["activity_type"] for entry in entries}
    assert types == {"strength", "cardio", "mobility"}
    for entry in entries:
        assert set(entry) == {"name", "activity_type"}
        assert entry["name"] == entry["name"].strip() and entry["name"]


def test_allowed_names_keep_the_listed_spelling() -> None:
    names = plan_checks.allowed_names()
    assert "Goblet squat" in names
    assert "Cat-cow stretch" in names


def test_free_days() -> None:
    assert plan_checks.free_days(SLOTS[:3]) == {
        date(2026, 11, 23),
        date(2026, 11, 24),
        date(2026, 11, 25),
    }
    assert plan_checks.free_days([]) == set()
