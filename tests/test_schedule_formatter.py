"""Tests for schedule_formatter.py."""
import pytest
from unittest.mock import MagicMock

from cronclear.schedule_formatter import format_schedule, FormattedSchedule


def _entry(schedule: str, command: str = "/usr/bin/true") -> MagicMock:
    entry = MagicMock()
    entry.schedule = schedule
    entry.command = command
    entry.is_shortcut.return_value = schedule.startswith("@")
    return entry


def test_format_returns_formatted_schedule_instance():
    result = format_schedule(_entry("0 * * * *"))
    assert isinstance(result, FormattedSchedule)


def test_format_daily_midnight():
    result = format_schedule(_entry("0 0 * * *"))
    assert "Daily" in result.human
    assert result.is_shortcut is False


def test_format_hourly_explicit():
    result = format_schedule(_entry("0 * * * *"))
    assert "hour" in result.human.lower() or "Daily" in result.human


def test_format_every_minute():
    result = format_schedule(_entry("* * * * *"))
    assert "minute" in result.human.lower()


def test_format_every_5_minutes():
    result = format_schedule(_entry("*/5 * * * *"))
    assert "5" in result.human
    assert "minute" in result.human.lower()


def test_format_shortcut_reboot():
    result = format_schedule(_entry("@reboot"))
    assert result.is_shortcut is True
    assert "reboot" in result.human.lower()


def test_format_shortcut_daily():
    result = format_schedule(_entry("@daily"))
    assert result.is_shortcut is True
    assert "day" in result.human.lower() or "midnight" in result.human.lower()


def test_format_shortcut_hourly():
    result = format_schedule(_entry("@hourly"))
    assert result.is_shortcut is True
    assert "hour" in result.human.lower()


def test_format_weekly_dow():
    result = format_schedule(_entry("0 9 * * 1"))
    assert "Mon" in result.human


def test_format_dow_range():
    result = format_schedule(_entry("0 8 * * 1-5"))
    assert "Mon" in result.human or "–" in result.human


def test_format_specific_month():
    result = format_schedule(_entry("0 0 1 12 *"))
    assert "Dec" in result.human


def test_format_comma_separated_days():
    result = format_schedule(_entry("0 9 * * 1,3,5"))
    assert "Mon" in result.human
    assert "Wed" in result.human
    assert "Fri" in result.human


def test_format_raw_preserved():
    schedule = "30 6 * * *"
    result = format_schedule(_entry(schedule))
    assert result.raw == schedule


def test_format_str_returns_human():
    result = format_schedule(_entry("0 0 * * *"))
    assert str(result) == result.human


def test_format_unknown_shortcut_returns_raw():
    result = format_schedule(_entry("@unknown"))
    assert result.is_shortcut is True
    assert result.human == "@unknown"
