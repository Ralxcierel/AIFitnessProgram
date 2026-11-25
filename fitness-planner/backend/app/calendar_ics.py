"""Calendar parser and free-slot finder for Fitness Planner.

Parses iCalendar (.ics) files and identifies free time slots between
configurable daily operating hours (defaults: 06:00 to 22:00, >= 45 minutes)
over an expanded 7-day period.

Course rules: Only free time slots reach the LLM — event titles, summaries,
and descriptions are explicitly stripped and never returned.
"""

from datetime import date, datetime, time, timedelta
from typing import Sequence
import icalendar

from .schemas import FreeSlot


def _to_naive_datetime(dt_val: datetime | date, default_time: time = time(0, 0)) -> datetime:
    """Normalize date or datetime to a naive datetime for consistent interval math.

    If timezone-aware, converts to local system timezone first, then strips tzinfo.
    """
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is not None:
            # Convert to local timezone before stripping tzinfo
            dt_val = dt_val.astimezone().replace(tzinfo=None)
        return dt_val
    elif isinstance(dt_val, date):
        return datetime.combine(dt_val, default_time)
    raise TypeError(f"Expected date or datetime, got {type(dt_val)}")


def _merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Merge overlapping or contiguous time intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: list[tuple[datetime, datetime]] = [sorted_intervals[0]]

    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            # Overlapping or contiguous; extend end if needed
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def find_free_slots(
    ics_content: str | bytes,
    start_date: date | None = None,
    days: int = 7,
    min_minutes: int = 45,
    day_start_hour: int = 6,
    day_end_hour: int = 22,
) -> list[FreeSlot]:
    """Parse .ics calendar and return free time slots of at least min_minutes.

    Args:
        ics_content: Raw .ics file contents as string or bytes.
        start_date: Starting calendar date (defaults to date.today()).
        days: Number of consecutive days to inspect (default: 7).
        min_minutes: Minimum duration in minutes for a free slot (default: 45).
        day_start_hour: Daily window start hour (default: 6 -> 06:00).
        day_end_hour: Daily window end hour (default: 22 -> 22:00).

    Returns:
        List of FreeSlot objects, each with start and end datetime.
    """
    if start_date is None:
        start_date = date.today()

    if isinstance(ics_content, str):
        ics_bytes = ics_content.encode("utf-8")
    else:
        ics_bytes = ics_content

    if not ics_bytes.strip():
        # Treat completely empty file/string as no busy events
        cal = icalendar.Calendar()
    else:
        try:
            cal = icalendar.Calendar.from_ical(ics_bytes)
        except Exception as err:
            raise ValueError(f"Invalid .ics calendar format: {err}") from err

    # Extract all busy intervals from VEVENT components
    raw_busy_intervals: list[tuple[datetime, datetime]] = []

    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            duration = component.get("duration")

            if not dtstart:
                continue

            start_dt = _to_naive_datetime(dtstart.dt, time(0, 0))

            if dtend:
                # In RFC 5545, date-only DTEND is non-inclusive midnight (time(0, 0))
                end_dt = _to_naive_datetime(dtend.dt, time(0, 0))
            elif duration:
                end_dt = start_dt + duration.dt
            else:
                # If no end and no duration, default to full day or 1-hour event
                if isinstance(dtstart.dt, date) and not isinstance(dtstart.dt, datetime):
                    end_dt = start_dt + timedelta(days=1)
                else:
                    end_dt = start_dt + timedelta(hours=1)

            if end_dt > start_dt:
                raw_busy_intervals.append((start_dt, end_dt))

    merged_busy = _merge_intervals(raw_busy_intervals)

    free_slots: list[FreeSlot] = []
    min_duration = timedelta(minutes=min_minutes)

    # Process day by day over the window
    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        window_start = datetime.combine(current_day, time(day_start_hour, 0))
        window_end = datetime.combine(current_day, time(day_end_hour, 0))

        # Filter busy intervals that overlap with this day's active window
        day_busy: list[tuple[datetime, datetime]] = []
        for b_start, b_end in merged_busy:
            if b_end <= window_start or b_start >= window_end:
                continue
            # Clip busy interval to day window
            clipped_start = max(b_start, window_start)
            clipped_end = min(b_end, window_end)
            if clipped_end > clipped_start:
                day_busy.append((clipped_start, clipped_end))

        day_busy = _merge_intervals(day_busy)

        # Invert day_busy to find free intervals
        cursor = window_start
        for b_start, b_end in day_busy:
            if b_start > cursor:
                gap = b_start - cursor
                if gap >= min_duration:
                    free_slots.append(FreeSlot(start=cursor, end=b_start))
            cursor = max(cursor, b_end)

        # Check tail interval after last busy block
        if window_end > cursor:
            gap = window_end - cursor
            if gap >= min_duration:
                free_slots.append(FreeSlot(start=cursor, end=window_end))

    return free_slots
