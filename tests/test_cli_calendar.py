"""Tests for cli_calendar module."""
import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronclear.cli_calendar import build_calendar_parser, run_calendar_command, _shade
from cronclear.schedule_calendar import CalendarCell, WeeklyCalendar, DAYS, HOURS


def _parse(args: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_calendar_parser(sub)
    return parser.parse_args(args)


# --- _shade helper ---

def test_shade_zero():
    assert _shade(0) == " "


def test_shade_low():
    assert _shade(1) == "░"
    assert _shade(2) == "░"


def test_shade_medium():
    assert _shade(4) == "▒"


def test_shade_high():
    assert _shade(8) == "▓"


def test_shade_max():
    assert _shade(20) == "█"


# --- parser ---

def test_parser_hosts():
    ns = _parse(["calendar", "host1", "host2"])
    assert ns.hosts == ["host1", "host2"]


def test_parser_defaults():
    ns = _parse(["calendar", "myhost"])
    assert ns.user == "root"
    assert ns.key_file is None
    assert ns.password is None


# --- run_calendar_command ---

def _fake_cal() -> WeeklyCalendar:
    cal = WeeklyCalendar(cells={day: {h: CalendarCell(day=day, hour=h) for h in HOURS} for day in DAYS})
    cal.cells["Mon"][10].entries.append(MagicMock())
    return cal


@patch("cronclear.cli_calendar.build_calendar")
@patch("cronclear.cli_calendar.CronCollector")
def test_run_returns_0_with_entries(mock_collector_cls, mock_build, capsys):
    entry = MagicMock()
    result = MagicMock()
    result.entries = [entry]
    mock_collector_cls.return_value.collect_from_hosts.return_value = [result]
    mock_build.return_value = _fake_cal()

    ns = _parse(["calendar", "host1"])
    code = run_calendar_command(ns)
    assert code == 0
    out = capsys.readouterr().out
    assert "Busiest slot" in out


@patch("cronclear.cli_calendar.CronCollector")
def test_run_returns_1_when_no_entries(mock_collector_cls, capsys):
    result = MagicMock()
    result.entries = []
    mock_collector_cls.return_value.collect_from_hosts.return_value = [result]

    ns = _parse(["calendar", "host1"])
    code = run_calendar_command(ns)
    assert code == 1
