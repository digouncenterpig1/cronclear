"""Tests for schedule_snapshot_diff module."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronclear.schedule_snapshot_diff import (
    diff_snapshots,
    SnapshotDiffReport,
    HostDiff,
)
from cronclear.schedule_watcher import Snapshot
from cronclear.cron_parser import CronEntry


def _entry(schedule: str, command: str, host: str = "h1") -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.schedule = schedule
    e.command = command
    e.host = host
    e.user = "root"
    e.__str__ = lambda self: f"{schedule} {command}"
    return e


def _snap(host: str, entries) -> Snapshot:
    s = MagicMock(spec=Snapshot)
    s.host = host
    s.entries = entries
    return s


def test_diff_snapshots_no_changes():
    e = _entry("* * * * *", "/bin/job")
    old = _snap("h1", [e])
    new = _snap("h1", [e])
    report = diff_snapshots(old, new)
    assert not report.has_any_changes


def test_diff_snapshots_entry_added():
    e1 = _entry("0 * * * *", "/bin/a")
    e2 = _entry("0 2 * * *", "/bin/b")
    old = _snap("h1", [e1])
    new = _snap("h1", [e1, e2])
    report = diff_snapshots(old, new)
    assert report.has_any_changes
    assert report.total_added == 1
    assert report.total_removed == 0


def test_diff_snapshots_entry_removed():
    e1 = _entry("0 * * * *", "/bin/a")
    e2 = _entry("0 2 * * *", "/bin/b")
    old = _snap("h1", [e1, e2])
    new = _snap("h1", [e1])
    report = diff_snapshots(old, new)
    assert report.has_any_changes
    assert report.total_removed == 1
    assert report.total_added == 0


def test_diff_snapshots_old_none_treats_all_as_added():
    e1 = _entry("0 * * * *", "/bin/a")
    e2 = _entry("0 2 * * *", "/bin/b")
    new = _snap("h1", [e1, e2])
    report = diff_snapshots(None, new)
    assert report.has_any_changes
    assert report.total_added == 2


def test_summary_lines_no_changes():
    e = _entry("* * * * *", "/bin/job")
    old = _snap("h1", [e])
    new = _snap("h1", [e])
    report = diff_snapshots(old, new)
    assert report.summary_lines() == []


def test_summary_lines_with_changes():
    e1 = _entry("0 * * * *", "/bin/a")
    e2 = _entry("0 2 * * *", "/bin/b")
    old = _snap("h1", [e1])
    new = _snap("h1", [e1, e2])
    report = diff_snapshots(old, new)
    lines = report.summary_lines()
    assert len(lines) == 1
    assert "h1" in lines[0]


def test_host_diff_has_changes_false_when_no_diff():
    from cronclear.schedule_differ import DiffResult
    dr = DiffResult(added=[], removed=[], unchanged=[])
    hd = HostDiff(host="h1", diff=dr)
    assert not hd.has_changes
