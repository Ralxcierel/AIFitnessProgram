"""Offline unit tests for profile storage in db.py (Step A2). Uses a throwaway database."""

from contextlib import closing
from pathlib import Path
import sqlite3
import sys

import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import db
from backend.app.schemas import UserProfile

SAMPLE = UserProfile(
    name="Sam Sample",
    height_cm=180,
    weight_kg=80,
    experience="beginner",
    goals=["get stronger"],
    workout_days=3,
    session_minutes=45,
    injuries=["sore left knee"],
    dietary_restrictions=["peanuts"],
)


@pytest.fixture(autouse=True)
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "app.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def read_rows(db_path: Path, query: str) -> list[tuple]:
    """Read the file with a separate connection, then close it."""
    with closing(sqlite3.connect(db_path)) as connection:
        return connection.execute(query).fetchall()


def test_empty_database_gives_an_empty_profile() -> None:
    assert db.load_profile() == UserProfile()


def test_first_use_creates_the_folder_and_file(db_path: Path) -> None:
    assert not db_path.parent.exists()
    db.load_profile()
    assert db_path.is_file()


def test_saved_profile_loads_back_the_same() -> None:
    assert db.save_profile(SAMPLE) == SAMPLE
    assert db.load_profile() == SAMPLE


def test_saving_again_replaces_the_profile(db_path: Path) -> None:
    db.save_profile(SAMPLE)
    newer = SAMPLE.model_copy(update={"weight_kg": 78.5, "goals": []})
    db.save_profile(newer)
    assert db.load_profile() == newer
    assert read_rows(db_path, "SELECT COUNT(*) FROM profile") == [(1,)]


def test_profile_is_on_disk_not_in_memory(db_path: Path) -> None:
    """The saved row is in the file, so it outlasts the server process."""
    db.save_profile(SAMPLE)
    rows = read_rows(db_path, "SELECT data FROM profile WHERE id = 1")
    assert UserProfile.model_validate_json(rows[0][0]) == SAMPLE


@pytest.mark.parametrize(
    "stored", ["{not json", '{"workout_days": 9}'], ids=["corrupt", "out-of-range"]
)
def test_unreadable_saved_profile_gives_an_empty_profile(
    db_path: Path, stored: str, caplog: pytest.LogCaptureFixture
) -> None:
    db.load_profile()  # creates the table
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("INSERT INTO profile (id, data) VALUES (1, ?)", (stored,))
    assert db.load_profile() == UserProfile()
    assert "unreadable" in caplog.text
    assert "workout_days" not in caplog.text
