"""Rule checks on a model-made weekly plan (Step B3, DESIGN.md §8).

Plain Python, no model call. check_plan() returns a list of plain-English
problems; an empty list means the plan passes. plan.py sends the problems back
to the model for one retry. Times are compared as local times with no time
zone (plan.py converts model times before checking).
"""

from datetime import date, datetime
from functools import cache
import json
from pathlib import Path

from .schemas import FreeSlot, Session, UserProfile, WeeklyPlan

EXERCISES_FILE = Path(__file__).resolve().parent / "data" / "exercises.json"
MAX_SESSIONS = 6
_MAX_QUOTED = 60  # longest exercise name quoted back in a problem


def normalize(name: str) -> str:
    """An exercise name for matching: case and extra spaces ignored."""
    return " ".join(name.split()).casefold()


@cache
def allowed_exercises() -> dict[str, tuple[str, str]]:
    """The allow-list: normalized name -> (name as listed, activity_type)."""
    entries = json.loads(EXERCISES_FILE.read_text(encoding="utf-8"))
    return {
        normalize(entry["name"]): (entry["name"], entry["activity_type"])
        for entry in entries
    }


def allowed_names() -> list[str]:
    """Exercise names as listed in exercises.json, in file order."""
    return [name for name, _ in allowed_exercises().values()]


def free_days(slots: list[FreeSlot]) -> set[date]:
    """The days that have at least one free slot."""
    return {slot.start.date() for slot in slots}


def check_plan(
    plan: WeeklyPlan, profile: UserProfile, slots: list[FreeSlot]
) -> list[str]:
    """Every rule the plan breaks, as short plain-English problems."""
    problems = _count_problems(plan, profile)
    seen_days: set[date] = set()
    for number, session in enumerate(plan.sessions, start=1):
        label = f"Session {number} ({_when(session.start)})"
        problems.extend(_time_problems(label, session, profile, slots))
        day = session.start.date()
        if day in seen_days:
            problems.append(f"{label} is on a day that already has a session.")
        seen_days.add(day)
        problems.extend(_exercise_problems(label, session))
    return problems


def _count_problems(plan: WeeklyPlan, profile: UserProfile) -> list[str]:
    """Number of sessions and rest days."""
    problems = []
    count = len(plan.sessions)
    if profile.workout_days is not None and count != profile.workout_days:
        problems.append(
            f"The plan has {count} sessions, but the profile asks for "
            f"{profile.workout_days}."
        )
    if count > MAX_SESSIONS:
        problems.append(f"The plan has {count} sessions; the most allowed is 6.")
    if len({session.start.date() for session in plan.sessions}) >= 7:
        problems.append("The plan has no rest day.")
    return problems


def _time_problems(
    label: str, session: Session, profile: UserProfile, slots: list[FreeSlot]
) -> list[str]:
    """Start before end, length limit, and fit inside one free slot."""
    if session.end <= session.start:
        return [f"{label} does not end after it starts."]
    problems = []
    minutes = (session.end - session.start).total_seconds() / 60
    if profile.session_minutes is not None and minutes > profile.session_minutes:
        problems.append(
            f"{label} is {minutes:g} minutes long; the most allowed is "
            f"{profile.session_minutes}."
        )
    if not any(s.start <= session.start and session.end <= s.end for s in slots):
        problems.append(f"{label} is not fully inside one free time slot.")
    return problems


def _exercise_problems(label: str, session: Session) -> list[str]:
    """Every exercise is on the allow-list with the listed activity type."""
    problems = []
    allowed = allowed_exercises()
    for exercise in session.exercises:
        quoted = exercise.name[:_MAX_QUOTED]
        match = allowed.get(normalize(exercise.name))
        if match is None:
            problems.append(f'{label}: "{quoted}" is not on the exercise list.')
        elif match[1] != exercise.activity_type:
            problems.append(
                f'{label}: "{match[0]}" is {match[1]}, not {exercise.activity_type}.'
            )
    return problems


def _when(moment: datetime) -> str:
    """A short day and time, e.g. "Mon 23 Nov 06:00"."""
    return moment.strftime("%a %d %b %H:%M")
