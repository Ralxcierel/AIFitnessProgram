"""Workout log and personal bests (Step A4). No model calls here.

Personal bests are computed in Python from the saved log entries (DESIGN.md §6).
"""

from fastapi import APIRouter
from pydantic import Field, field_validator

from . import db
from .schemas import LogEntry, PersonalBest

MAX_EXERCISE_LENGTH = 100
MAX_SETS_OR_REPS = 1000
MAX_WEIGHT_KG = 1000


class NewLogEntry(LogEntry):
    """A LogEntry sent by the user: the name is trimmed and checked.

    The upper limits keep numbers within what SQLite can store (huge numbers
    would otherwise fail with a 500) and reject Infinity / NaN weights.
    """

    sets: int = Field(ge=1, le=MAX_SETS_OR_REPS)
    reps: int = Field(ge=1, le=MAX_SETS_OR_REPS)
    weight_kg: float | None = Field(None, ge=0, le=MAX_WEIGHT_KG, allow_inf_nan=False)

    @field_validator("exercise")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("exercise must not be blank")
        if len(name) > MAX_EXERCISE_LENGTH:
            raise ValueError(f"exercise must be at most {MAX_EXERCISE_LENGTH} characters")
        return name


router = APIRouter()


@router.post("/api/log")
def add_entry(entry: NewLogEntry) -> LogEntry:
    """Save one logged exercise; the server assigns the id."""
    return db.add_log_entry(LogEntry.model_validate(entry.model_dump()))


@router.get("/api/log")
def list_entries() -> list[LogEntry]:
    """All logged exercises, newest first."""
    return db.list_log_entries()


@router.get("/api/log/bests")
def bests() -> list[PersonalBest]:
    """The heaviest weight per exercise, sorted by exercise name."""
    return personal_bests(db.list_log_entries())


def exercise_key(name: str) -> str:
    """Names that differ only in spacing or letter case are the same exercise."""
    return " ".join(name.split()).casefold()


def personal_bests(entries: list[LogEntry]) -> list[PersonalBest]:
    """Heaviest weight per exercise; a tie keeps the earliest date.

    Entries without a weight have no personal best. Each exercise is shown by
    the name it was first logged under.
    """
    first_name: dict[str, str] = {}
    best: dict[str, PersonalBest] = {}
    for entry in sorted(entries, key=lambda e: (e.id is None, e.id or 0)):
        key = exercise_key(entry.exercise)
        first_name.setdefault(key, entry.exercise)
        if entry.weight_kg is None:
            continue
        current = best.get(key)
        if (
            current is None
            or entry.weight_kg > current.best_weight_kg
            or (entry.weight_kg == current.best_weight_kg and entry.date < current.date)
        ):
            best[key] = PersonalBest(
                exercise=first_name[key],
                best_weight_kg=entry.weight_kg,
                date=entry.date,
            )
    return sorted(best.values(), key=lambda b: exercise_key(b.exercise))
