"""Offline tests for the workout log and personal bests (Step A4).

Nothing here calls the API; every test uses a throwaway database.
"""

from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient
import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import db, main, workout_log
from backend.app.schemas import LogEntry, PersonalBest

LOG_URL = "/api/log"
BESTS_URL = "/api/log/bests"


@pytest.fixture(autouse=True)
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "app.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


def entry(
    day: str, exercise: str, weight: float | None, id_: int | None = None
) -> LogEntry:
    return LogEntry(
        id=id_, date=date.fromisoformat(day), exercise=exercise, sets=3, reps=5,
        weight_kg=weight,
    )


# --- personal_bests(): the calculation on its own ---------------------------


def test_no_entries_means_no_bests() -> None:
    assert workout_log.personal_bests([]) == []


def test_best_is_the_heaviest_weight() -> None:
    entries = [
        entry("2026-11-01", "Squat", 60, 1),
        entry("2026-11-03", "Squat", 80, 2),
        entry("2026-11-05", "Squat", 70, 3),
    ]
    assert workout_log.personal_bests(entries) == [
        PersonalBest(exercise="Squat", best_weight_kg=80, date=date(2026, 11, 3))
    ]


def test_a_tie_keeps_the_earliest_date() -> None:
    entries = [
        entry("2026-11-05", "Squat", 80, 1),
        entry("2026-11-02", "Squat", 80, 2),
        entry("2026-11-09", "Squat", 80, 3),
    ]
    assert workout_log.personal_bests(entries)[0].date == date(2026, 11, 2)


def test_entries_without_weight_have_no_best() -> None:
    entries = [
        entry("2026-11-01", "Push-up", None, 1),
        entry("2026-11-02", "Squat", None, 2),
        entry("2026-11-03", "Squat", 40, 3),
    ]
    assert workout_log.personal_bests(entries) == [
        PersonalBest(exercise="Squat", best_weight_kg=40, date=date(2026, 11, 3))
    ]


def test_zero_weight_counts_as_a_weight() -> None:
    best = workout_log.personal_bests([entry("2026-11-01", "Plank", 0, 1)])
    assert best == [PersonalBest(exercise="Plank", best_weight_kg=0, date=date(2026, 11, 1))]


def test_names_match_ignoring_case_and_spacing_and_keep_the_first_name() -> None:
    entries = [
        entry("2026-11-04", "bench  PRESS", 70, 2),
        entry("2026-11-01", "Bench Press", 60, 1),
        entry("2026-11-06", " bench press ", 65, 3),
    ]
    assert workout_log.personal_bests(entries) == [
        PersonalBest(exercise="Bench Press", best_weight_kg=70, date=date(2026, 11, 4))
    ]


def test_bests_are_sorted_by_exercise_name() -> None:
    entries = [
        entry("2026-11-01", "squat", 80, 1),
        entry("2026-11-01", "Bench Press", 60, 2),
        entry("2026-11-01", "Deadlift", 100, 3),
    ]
    names = [best.exercise for best in workout_log.personal_bests(entries)]
    assert names == ["Bench Press", "Deadlift", "squat"]


# --- storage -----------------------------------------------------------------


def test_saved_entries_get_new_ids_and_list_newest_first() -> None:
    first = db.add_log_entry(entry("2026-11-01", "Squat", 60))
    second = db.add_log_entry(entry("2026-11-03", "Squat", 65))
    same_day = db.add_log_entry(entry("2026-11-03", "Row", 40))
    assert (first.id, second.id, same_day.id) == (1, 2, 3)
    assert db.list_log_entries() == [same_day, second, first]


def test_entries_are_on_disk(db_path: Path) -> None:
    db.add_log_entry(entry("2026-11-01", "Squat", 60))
    with closing(sqlite3.connect(db_path)) as connection:
        rows = connection.execute("SELECT date, exercise, weight_kg FROM log_entries").fetchall()
    assert rows == [("2026-11-01", "Squat", 60.0)]


def test_unreadable_row_is_skipped(
    db_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    good = db.add_log_entry(entry("2026-11-01", "Squat", 60))
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute(
            "INSERT INTO log_entries (date, exercise, sets, reps, weight_kg)"
            " VALUES ('not a date', 'SECRET', 0, 5, NULL)"
        )
    assert db.list_log_entries() == [good]
    assert "unreadable" in caplog.text
    assert "SECRET" not in caplog.text


# --- endpoints ---------------------------------------------------------------


def test_post_saves_and_returns_the_entry_with_an_id(client: TestClient) -> None:
    body = {"date": "2026-11-20", "exercise": "  Squat ", "sets": 3, "reps": 5,
            "weight_kg": 62.5}
    result = client.post(LOG_URL, json=body)
    assert result.status_code == 200
    assert result.json() == {**body, "exercise": "Squat", "id": 1}
    assert client.get(LOG_URL).json() == [result.json()]


def test_post_ignores_a_sent_id(client: TestClient) -> None:
    body = {"id": 99, "date": "2026-11-20", "exercise": "Squat", "sets": 3, "reps": 5}
    assert client.post(LOG_URL, json=body).json()["id"] == 1
    assert client.post(LOG_URL, json=body).json()["id"] == 2


def test_weight_is_optional(client: TestClient) -> None:
    body = {"date": "2026-11-20", "exercise": "Push-up", "sets": 3, "reps": 15}
    assert client.post(LOG_URL, json=body).json()["weight_kg"] is None


def test_get_log_is_empty_at_first(client: TestClient) -> None:
    assert client.get(LOG_URL).json() == []
    assert client.get(BESTS_URL).json() == []


def test_bests_endpoint_uses_the_saved_log(client: TestClient) -> None:
    for day, weight in [("2026-11-01", 60), ("2026-11-08", 70), ("2026-11-15", 70)]:
        client.post(
            LOG_URL,
            json={"date": day, "exercise": "Squat", "sets": 3, "reps": 5, "weight_kg": weight},
        )
    assert client.get(BESTS_URL).json() == [
        {"exercise": "Squat", "best_weight_kg": 70.0, "date": "2026-11-08"}
    ]


@pytest.mark.parametrize(
    "change, where",
    [
        ({"exercise": "   "}, "exercise"),
        ({"exercise": "x" * 101}, "exercise"),
        ({"exercise": None}, "exercise"),
        ({"sets": 0}, "sets"),
        ({"reps": 0}, "reps"),
        ({"weight_kg": -1}, "weight_kg"),
        ({"date": "SECRET"}, "date"),
        ({"sets": "SECRET"}, "sets"),
        ({"sets": 1001}, "sets"),
        ({"reps": 10**20}, "reps"),
        ({"weight_kg": 1000.5}, "weight_kg"),
    ],
)
def test_bad_entries_use_the_shared_error_format_and_are_not_saved(
    client: TestClient, change: dict, where: str
) -> None:
    body = {"date": "2026-11-20", "exercise": "Squat", "sets": 3, "reps": 5, **change}
    result = client.post(LOG_URL, json=body)
    assert result.status_code == 422
    assert set(result.json()) == {"error", "detail"}
    assert where in result.json()["detail"]
    assert "SECRET" not in result.text
    assert client.get(LOG_URL).json() == []


@pytest.mark.parametrize("weight", ["Infinity", "NaN", "-Infinity"])
def test_infinite_or_nan_weight_is_rejected(client: TestClient, weight: str) -> None:
    content = (
        '{"date": "2026-11-20", "exercise": "Squat", "sets": 3, "reps": 5,'
        f' "weight_kg": {weight}}}'
    )
    result = client.post(
        LOG_URL, content=content, headers={"content-type": "application/json"}
    )
    assert result.status_code == 422
    assert set(result.json()) == {"error", "detail"}
    assert client.get(LOG_URL).json() == []


def test_the_upper_limits_themselves_are_allowed(client: TestClient) -> None:
    body = {"date": "2026-11-20", "exercise": "Squat", "sets": 1000, "reps": 1000,
            "weight_kg": 1000}
    assert client.post(LOG_URL, json=body).status_code == 200


def test_whole_and_decimal_weights_tie() -> None:
    entries = [entry("2026-11-05", "Squat", 60, 1), entry("2026-11-02", "Squat", 60.0, 2)]
    assert workout_log.personal_bests(entries)[0].date == date(2026, 11, 2)


def test_display_name_is_the_first_logged_even_if_the_best_is_written_differently() -> None:
    entries = [
        entry("2026-11-01", "Deadlift", None, 1),
        entry("2026-11-02", "DEADLIFT", 100, 2),
        entry("2026-11-03", "deadlift", 120, 3),
    ]
    assert workout_log.personal_bests(entries) == [
        PersonalBest(exercise="Deadlift", best_weight_kg=120, date=date(2026, 11, 3))
    ]


def test_a_100_character_name_is_allowed(client: TestClient) -> None:
    body = {"date": "2026-11-20", "exercise": "x" * 100, "sets": 1, "reps": 1}
    assert client.post(LOG_URL, json=body).status_code == 200


def test_wrong_method_uses_the_shared_error_format(client: TestClient) -> None:
    result = client.put(LOG_URL, json={})
    assert result.status_code == 405
    assert result.json() == {"error": "Method Not Allowed", "detail": None}
