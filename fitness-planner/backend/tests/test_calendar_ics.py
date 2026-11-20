"""Unit tests for .ics calendar parser and free-slot finder (Step B1)."""

from datetime import date, datetime
from pathlib import Path
import sys
import pytest

# Ensure fitness-planner root is on sys.path regardless of execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.calendar_ics import FreeSlot, find_free_slots

FIXTURES_DIR = PROJECT_ROOT / "eval" / "fixtures"


@pytest.fixture
def empty_ics() -> str:
    with open(FIXTURES_DIR / "empty.ics", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def normal_ics() -> str:
    with open(FIXTURES_DIR / "normal.ics", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def packed_ics() -> str:
    with open(FIXTURES_DIR / "packed.ics", "r", encoding="utf-8") as f:
        return f.read()


def test_empty_calendar_returns_full_day_slots(empty_ics: str) -> None:
    """Empty calendar should return 7 full free slots (06:00 to 22:00 = 16 hours each)."""
    start_date = date(2026, 11, 23)
    slots = find_free_slots(empty_ics, start_date=start_date, days=7)

    assert len(slots) == 7
    for i, slot in enumerate(slots):
        expected_day = date(2026, 11, 23 + i)
        assert slot.start == datetime(expected_day.year, expected_day.month, expected_day.day, 6, 0)
        assert slot.end == datetime(expected_day.year, expected_day.month, expected_day.day, 22, 0)
        # Duration is 16 hours = 960 minutes
        duration_minutes = (slot.end - slot.start).total_seconds() / 60
        assert duration_minutes == 960


def test_normal_calendar_has_workday_and_weekend_slots(normal_ics: str) -> None:
    """Normal calendar has 9-12 and 13-17 busy blocks on Mon-Thu, and 9-12 and 13-16 on Fri."""
    start_date = date(2026, 11, 23)  # Monday
    slots = find_free_slots(normal_ics, start_date=start_date, days=7)

    # Monday slots expected:
    # 06:00-09:00 (3 hrs)
    # 12:00-13:00 (1 hr lunch >= 45m)
    # 17:00-22:00 (5 hrs)
    mon_slots = [s for s in slots if s.start.date() == start_date]
    assert len(mon_slots) == 3
    assert mon_slots[0].start == datetime(2026, 11, 23, 6, 0)
    assert mon_slots[0].end == datetime(2026, 11, 23, 9, 0)
    assert mon_slots[1].start == datetime(2026, 11, 23, 12, 0)
    assert mon_slots[1].end == datetime(2026, 11, 23, 13, 0)
    assert mon_slots[2].start == datetime(2026, 11, 23, 17, 0)
    assert mon_slots[2].end == datetime(2026, 11, 23, 22, 0)

    # Weekend (Sat 2026-11-28 and Sun 2026-11-29) should be completely free (06:00-22:00)
    sat_slots = [s for s in slots if s.start.date() == date(2026, 11, 28)]
    assert len(sat_slots) == 1
    assert sat_slots[0].start == datetime(2026, 11, 28, 6, 0)
    assert sat_slots[0].end == datetime(2026, 11, 28, 22, 0)


def test_packed_calendar_filters_short_gaps(packed_ics: str) -> None:
    """Packed calendar: Monday has a 30m gap (12:00-12:30 busy, but no free slot >= 45 min).

    Sunday has 21:00-22:00 (60m free slot >= 45 min).
    """
    start_date = date(2026, 11, 23)
    slots = find_free_slots(packed_ics, start_date=start_date, days=7)

    # Monday has 0 free slots because 06:00-12:00, 12:00-12:30, 12:30-17:00, 17:00-22:00 are busy
    mon_slots = [s for s in slots if s.start.date() == start_date]
    assert len(mon_slots) == 0

    # Tue-Sat are all-day marathons (06:00-22:00 busy) -> 0 slots
    for day in range(24, 29):
        day_slots = [s for s in slots if s.start.date() == date(2026, 11, day)]
        assert len(day_slots) == 0

    # Sunday has conference until 21:00, leaving 21:00-22:00 free (60m >= 45m)
    sun_slots = [s for s in slots if s.start.date() == date(2026, 11, 29)]
    assert len(sun_slots) == 1
    assert sun_slots[0].start == datetime(2026, 11, 29, 21, 0)
    assert sun_slots[0].end == datetime(2026, 11, 29, 22, 0)


def test_all_day_event_non_inclusive_end() -> None:
    """RFC 5545 all-day event on Monday (DTSTART:20261123, DTEND:20261124) must only occupy Monday."""
    ics_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:allday-mon@test
DTSTART;VALUE=DATE:20261123
DTEND;VALUE=DATE:20261124
SUMMARY:All-day Conference
END:VEVENT
END:VCALENDAR"""
    slots = find_free_slots(ics_text, start_date=date(2026, 11, 23), days=2)

    # Monday (2026-11-23) is fully occupied by the all-day event
    mon_slots = [s for s in slots if s.start.date() == date(2026, 11, 23)]
    assert len(mon_slots) == 0

    # Tuesday (2026-11-24) must be completely free (06:00 to 22:00)
    tue_slots = [s for s in slots if s.start.date() == date(2026, 11, 24)]
    assert len(tue_slots) == 1
    assert tue_slots[0].start == datetime(2026, 11, 24, 6, 0)
    assert tue_slots[0].end == datetime(2026, 11, 24, 22, 0)


def test_overlapping_and_adjacent_busy_events() -> None:
    """Overlapping events in raw ICS must be merged correctly without gaps."""
    ics_text = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:overlap-1@test
DTSTART:20261123T080000
DTEND:20261123T110000
SUMMARY:Event 1
END:VEVENT
BEGIN:VEVENT
UID:overlap-2@test
DTSTART:20261123T100000
DTEND:20261123T130000
SUMMARY:Overlapping Event 2
END:VEVENT
END:VCALENDAR"""
    slots = find_free_slots(ics_text, start_date=date(2026, 11, 23), days=1)
    # Day window: 06:00 to 22:00. Busy: 08:00 to 13:00.
    # Expected free slots: 06:00-08:00 (120m) and 13:00-22:00 (540m).
    assert len(slots) == 2
    assert slots[0].start == datetime(2026, 11, 23, 6, 0)
    assert slots[0].end == datetime(2026, 11, 23, 8, 0)
    assert slots[1].start == datetime(2026, 11, 23, 13, 0)
    assert slots[1].end == datetime(2026, 11, 23, 22, 0)


def test_invalid_ics_raises_value_error() -> None:
    """Invalid ics syntax should raise a clear ValueError."""
    with pytest.raises(ValueError, match="Invalid .ics calendar format"):
        find_free_slots("INVALID ICS CONTENT THAT CANNOT BE PARSED")
