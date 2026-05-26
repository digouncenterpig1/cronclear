"""Tests for schedule_calendar module."""
import pytest
from unittest.mock import MagicMock

from cronclear.cron_parser import CronEntry
from cronclear.schedule_calendar import (
    CalendarCell,
    WeeklyCalendar,
    build_calendar,
    _expand_field,
    DAYS,
)


def _entry(schedule: str, cmd: str = "backup.sh") -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.schedule = schedule
    e.command = cmd
    e.is_shortcut.return_value = False
    return e


def _shortcut(schedule: str = "@daily") -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.schedule = schedule
    e.is_shortcut.return_value = True
    return e


# --- _expand_field ---

def test_expand_star():
    assert _expand_field("*", 0, 6) == list(range(7))


def test_expand_single():
    assert _expand_field("3", 0, 23) == [3]


def test_expand_range():
    assert _expand_field("2-4", 0, 23) == [2, 3, 4]


def test_expand_step():
    result = _expand_field("*/6", 0, 23)
    assert result == [0, 6, 12, 18]


def test_expand_list():
    assert _expand_field("1,3,5", 0, 6) == [1, 3, 5]


# --- build_calendar ---

def test_build_calendar_skips_shortcuts():
    entries = [_shortcut()]
    cal = build_calendar(entries)
    assert cal.total_slots_used() == 0


def test_build_calendar_populates_cell():
    # runs every day at 02:00
    e = _entry("0 2 * * *")
    cal = build_calendar([e])
    for day in DAYS:
        cell = cal.get(day, 2)
        assert cell.count == 1


def test_build_calendar_specific_day():
    # runs only on Monday (dow=1) at 10:00
    e = _entry("0 10 * * 1")
    cal = build_calendar([e])
    assert cal.get("Mon", 10).count == 1
    assert cal.get("Tue", 10).count == 0


def test_busiest_slot_correct():
    entries = [_entry("0 5 * * *") for _ in range(3)]
    cal = build_calendar(entries)
    slot = cal.busiest_slot()
    assert slot.hour == 5
    assert slot.count == 3


def test_total_slots_used():
    # one entry running every hour every day fills all 168 slots
    e = _entry("0 * * * *")
    cal = build_calendar([e])
    assert cal.total_slots_used() == 7 * 24


def test_calendar_cell_defaults():
    cell = CalendarCell(day="Fri", hour=9)
    assert cell.count == 0
    assert cell.entries == []


def test_build_calendar_ignores_bad_schedule():
    e = MagicMock(spec=CronEntry)
    e.schedule = "bad"
    e.is_shortcut.return_value = False
    cal = build_calendar([e])
    assert cal.total_slots_used() == 0


def test_build_calendar_multiple_entries_same_slot():
    """Multiple entries scheduled at the same day/hour should stack in the cell."""
    entries = [
        _entry("0 8 * * 1", cmd="job_a.sh"),
        _entry("0 8 * * 1", cmd="job_b.sh"),
        _entry("0 8 * * 1", cmd="job_c.sh"),
    ]
    cal = build_calendar(entries)
    cell = cal.get("Mon", 8)
    assert cell.count == 3
    # other days at the same hour should be unaffected
    assert cal.get("Wed", 8).count == 0
