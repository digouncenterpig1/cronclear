"""Integration tests: full round-trip snapshot diff via watcher + differ."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock

from cronclear.schedule_watcher import Snapshot, save_snapshot, load_snapshot
from cronclear.schedule_snapshot_diff import diff_snapshots
from cronclear.cron_parser import CronEntry


def _e(sched: str, cmd: str, host: str = "web01") -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.schedule = sched
    e.command = cmd
    e.host = host
    e.user = "root"
    e.__str__ = lambda self: f"{sched} {cmd}"
    return e


def test_integration_no_changes():
    e1 = _e("0 * * * *", "/usr/bin/backup")
    snap = Snapshot(host="web01", entries=[e1])
    report = diff_snapshots(snap, snap)
    assert not report.has_any_changes
    assert report.total_added == 0
    assert report.total_removed == 0


def test_integration_added_entry():
    e1 = _e("0 * * * *", "/usr/bin/backup")
    e2 = _e("30 2 * * *", "/usr/bin/cleanup")
    old = Snapshot(host="web01", entries=[e1])
    new = Snapshot(host="web01", entries=[e1, e2])
    report = diff_snapshots(old, new)
    assert report.has_any_changes
    assert report.total_added == 1
    assert report.total_removed == 0
    lines = report.summary_lines()
    assert any("web01" in l for l in lines)


def test_integration_removed_entry():
    e1 = _e("0 * * * *", "/usr/bin/backup")
    e2 = _e("30 2 * * *", "/usr/bin/cleanup")
    old = Snapshot(host="web01", entries=[e1, e2])
    new = Snapshot(host="web01", entries=[e1])
    report = diff_snapshots(old, new)
    assert report.has_any_changes
    assert report.total_removed == 1


def test_integration_first_run_no_old_snapshot():
    e1 = _e("0 * * * *", "/usr/bin/backup")
    e2 = _e("30 2 * * *", "/usr/bin/cleanup")
    new = Snapshot(host="web01", entries=[e1, e2])
    report = diff_snapshots(None, new)
    assert report.has_any_changes
    assert report.total_added == 2
    assert len(report.summary_lines()) >= 1
