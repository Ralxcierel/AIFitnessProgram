"""SQLite storage for the single local user (Steps A2, A4 and B2).

The demo has one user and no login. The profile table holds at most one row:
the whole validated UserProfile as JSON text. The workout log has one row per
logged exercise. The calendar table holds the free slots of the latest upload
(times only, never event titles), and the plan table the current WeeklyPlan;
each has at most one row. The database file is gitignored.
"""

from datetime import date
import logging
from pathlib import Path
import sqlite3

from pydantic import TypeAdapter, ValidationError

from .schemas import FreeSlot, LogEntry, UserProfile, WeeklyPlan

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

_CREATE_PROFILE_TABLE = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
)
"""

_CREATE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS log_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    exercise TEXT NOT NULL,
    sets INTEGER NOT NULL,
    reps INTEGER NOT NULL,
    weight_kg REAL
)
"""

_CREATE_CALENDAR_TABLE = """
CREATE TABLE IF NOT EXISTS calendar (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    week_of TEXT NOT NULL,
    free_slots TEXT NOT NULL
)
"""

_CREATE_PLAN_TABLE = """
CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
)
"""

_SLOTS = TypeAdapter(list[FreeSlot])


def _connect() -> sqlite3.Connection:
    """Open the database, creating its folder and tables on first use."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.execute(_CREATE_PROFILE_TABLE)
        connection.execute(_CREATE_LOG_TABLE)
        connection.execute(_CREATE_CALENDAR_TABLE)
        connection.execute(_CREATE_PLAN_TABLE)
    except sqlite3.Error:
        connection.close()
        raise
    return connection


def load_profile() -> UserProfile:
    """Return the saved profile, or an empty one if none is saved or readable.

    A saved profile that no longer matches the schema (corrupted, or the schema
    changed) is treated as no profile; the warning holds no profile data.
    """
    connection = _connect()
    try:
        row = connection.execute("SELECT data FROM profile WHERE id = 1").fetchone()
    finally:
        connection.close()
    if row is None:
        return UserProfile()
    try:
        return UserProfile.model_validate_json(row[0])
    except ValidationError:
        log.warning("Saved profile is unreadable; starting with an empty profile")
        return UserProfile()


def save_profile(profile: UserProfile) -> UserProfile:
    """Replace the saved profile and return it."""
    connection = _connect()
    try:
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)",
                (profile.model_dump_json(),),
            )
    finally:
        connection.close()
    return profile


def add_log_entry(entry: LogEntry) -> LogEntry:
    """Save one workout log entry and return it with its new id.

    The database always assigns the id; any id on `entry` is ignored.
    """
    connection = _connect()
    try:
        with connection:
            cursor = connection.execute(
                "INSERT INTO log_entries (date, exercise, sets, reps, weight_kg)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    entry.date.isoformat(),
                    entry.exercise,
                    entry.sets,
                    entry.reps,
                    entry.weight_kg,
                ),
            )
    finally:
        connection.close()
    return entry.model_copy(update={"id": cursor.lastrowid})


def list_log_entries() -> list[LogEntry]:
    """All log entries, newest date first (newest entry first on the same day).

    A row that no longer matches the schema is skipped with a warning that
    holds no workout data.
    """
    connection = _connect()
    try:
        rows = connection.execute(
            "SELECT id, date, exercise, sets, reps, weight_kg FROM log_entries"
            " ORDER BY date DESC, id DESC"
        ).fetchall()
    finally:
        connection.close()
    entries = []
    for id_, date, exercise, sets, reps, weight_kg in rows:
        try:
            entries.append(
                LogEntry(
                    id=id_,
                    date=date,
                    exercise=exercise,
                    sets=sets,
                    reps=reps,
                    weight_kg=weight_kg,
                )
            )
        except ValidationError:
            log.warning("Skipped an unreadable workout log row (id %s)", id_)
    return entries


def save_free_slots(week_of: date, slots: list[FreeSlot]) -> None:
    """Replace the saved free slots with those of a new upload."""
    connection = _connect()
    try:
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO calendar (id, week_of, free_slots)"
                " VALUES (1, ?, ?)",
                (week_of.isoformat(), _SLOTS.dump_json(slots).decode()),
            )
    finally:
        connection.close()


def load_free_slots() -> tuple[date, list[FreeSlot]] | None:
    """The first day and free slots of the latest upload, or None if none is saved.

    Unreadable saved slots count as no upload; the warning holds no times.
    """
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT week_of, free_slots FROM calendar WHERE id = 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    try:
        return date.fromisoformat(row[0]), _SLOTS.validate_json(row[1])
    except (ValueError, ValidationError):
        log.warning("Saved free slots are unreadable; treating as no calendar")
        return None


def save_plan(plan: WeeklyPlan) -> WeeklyPlan:
    """Replace the current plan and return it."""
    connection = _connect()
    try:
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO plan (id, data) VALUES (1, ?)",
                (plan.model_dump_json(),),
            )
    finally:
        connection.close()
    return plan


def clear_plan() -> None:
    """Remove the current plan, if any."""
    connection = _connect()
    try:
        with connection:
            connection.execute("DELETE FROM plan WHERE id = 1")
    finally:
        connection.close()


def load_plan() -> WeeklyPlan | None:
    """The current plan, or None if none is saved or it is unreadable."""
    connection = _connect()
    try:
        row = connection.execute("SELECT data FROM plan WHERE id = 1").fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    try:
        return WeeklyPlan.model_validate_json(row[0])
    except ValidationError:
        log.warning("Saved plan is unreadable; treating as no plan")
        return None
