"""SQLite storage for the single local user's profile (Step A2).

The demo has one user and no login, so the table holds at most one row: the
whole validated UserProfile as JSON text. The database file is gitignored.
"""

import logging
from pathlib import Path
import sqlite3

from pydantic import ValidationError

from .schemas import UserProfile

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

_CREATE_PROFILE_TABLE = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
)
"""


def _connect() -> sqlite3.Connection:
    """Open the database, creating its folder and table on first use."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(_CREATE_PROFILE_TABLE)
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
