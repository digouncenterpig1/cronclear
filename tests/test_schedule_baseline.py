"""Tests for cronclear.schedule_baseline."""
import json
from pathlib import Path

import pytest

from cronclear.schedule_baseline import (
    BaselineEntry,
    BaselineReport,
    compare_to_baseline,
    load_baseline,
    save_baseline,
)
from cronclear.cron_parser import CronEntry


def _make_cron(raw: str, user: str = "root", host: str = "web1") -> CronEntry:
    return CronEntry(raw=raw, user=user, host=host)


def _make_baseline(raw: str, user: str = "root", host: str = "web1") -> BaselineEntry:
    return BaselineEntry(raw=raw, user=user, host=host)


# --- BaselineReport ---

def test_report_no_changes():
    r = BaselineReport()
    assert not r.has_changes
    assert r.summary_line() == "No changes from baseline."


def test_report_has_changes_added():
    r = BaselineReport(added=[_make_baseline("* * * * * echo hi")])
    assert r.has_changes
    assert "+1 added" in r.summary_line()


def test_report_has_changes_removed():
    r = BaselineReport(removed=[_make_baseline("0 * * * * echo bye")])
    assert r.has_changes
    assert "-1 removed" in r.summary_line()


def test_report_summary_both():
    r = BaselineReport(
        added=[_make_baseline("* * * * * a")],
        removed=[_make_baseline("0 0 * * * b"), _make_baseline("1 0 * * * c")],
    )
    line = r.summary_line()
    assert "+1 added" in line
    assert "-2 removed" in line


# --- save / load ---

def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "baseline.json"
    entries = [_make_cron("0 6 * * * backup"), _make_cron("*/5 * * * * check")]
    save_baseline(entries, p)
    loaded = load_baseline(p)
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0].raw == "0 6 * * * backup"
    assert loaded[1].host == "web1"


def test_load_missing_returns_none(tmp_path):
    result = load_baseline(tmp_path / "nonexistent.json")
    assert result is None


def test_save_writes_valid_json(tmp_path):
    p = tmp_path / "b.json"
    save_baseline([_make_cron("* * * * * x")], p)
    data = json.loads(p.read_text())
    assert isinstance(data, list)
    assert data[0]["raw"] == "* * * * * x"


# --- compare_to_baseline ---

def test_compare_no_changes():
    entries = [_make_cron("0 0 * * * job")]
    baseline = [_make_baseline("0 0 * * * job")]
    report = compare_to_baseline(entries, baseline)
    assert not report.has_changes


def test_compare_detects_added():
    entries = [_make_cron("0 0 * * * job"), _make_cron("5 * * * * new")]
    baseline = [_make_baseline("0 0 * * * job")]
    report = compare_to_baseline(entries, baseline)
    assert len(report.added) == 1
    assert report.added[0].raw == "5 * * * * new"
    assert not report.removed


def test_compare_detects_removed():
    entries = []
    baseline = [_make_baseline("0 0 * * * old")]
    report = compare_to_baseline(entries, baseline)
    assert len(report.removed) == 1
    assert not report.added


def test_compare_host_distinguishes_same_raw():
    entries = [_make_cron("* * * * * x", host="host_a")]
    baseline = [_make_baseline("* * * * * x", host="host_b")]
    report = compare_to_baseline(entries, baseline)
    assert len(report.added) == 1
    assert len(report.removed) == 1
