"""Tests for ScheduleWatcher and related helpers."""

import json
import os
from datetime import datetime, timezone

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.schedule_watcher import Snapshot, ScheduleWatcher, WatchReport


def _entry(user: str, schedule: str, command: str, host: str = "host1") -> CronEntry:
    return CronEntry(user=user, host=host, schedule=schedule, command=command)


# ---------------------------------------------------------------------------
# Snapshot serialisation
# ---------------------------------------------------------------------------

def test_snapshot_round_trip():
    entries = [_entry("root", "0 * * * *", "/bin/foo")]
    snap = Snapshot(
        host="host1",
        captured_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        entries=entries,
    )
    data = snap.to_dict()
    restored = Snapshot.from_dict(data)
    assert restored.host == "host1"
    assert len(restored.entries) == 1
    assert restored.entries[0].command == "/bin/foo"


def test_snapshot_from_dict_empty_entries():
    data = {
        "host": "h",
        "captured_at": "2024-01-01T00:00:00+00:00",
        "entries": [],
    }
    snap = Snapshot.from_dict(data)
    assert snap.entries == []


# ---------------------------------------------------------------------------
# ScheduleWatcher — persistence
# ---------------------------------------------------------------------------

def test_load_snapshot_returns_none_when_missing(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    assert watcher.load_snapshot("unknown-host") is None


def test_save_and_load_snapshot(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    entries = [_entry("deploy", "30 2 * * *", "/deploy.sh")]
    snap = Snapshot(
        host="web1",
        captured_at=datetime.now(timezone.utc),
        entries=entries,
    )
    watcher.save_snapshot(snap)
    loaded = watcher.load_snapshot("web1")
    assert loaded is not None
    assert loaded.host == "web1"
    assert loaded.entries[0].command == "/deploy.sh"


def test_snapshot_file_uses_safe_name(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    snap = Snapshot(host="host:8080", captured_at=datetime.now(timezone.utc), entries=[])
    watcher.save_snapshot(snap)
    files = os.listdir(str(tmp_path))
    assert any("8080" in f for f in files)
    assert not any(":" in f for f in files)


# ---------------------------------------------------------------------------
# ScheduleWatcher — diff logic
# ---------------------------------------------------------------------------

def test_watch_first_run_no_previous(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    entries = [_entry("root", "* * * * *", "/check.sh")]
    diff = watcher.watch("host1", entries)
    # first run: everything is added, nothing removed
    assert len(diff.added) == 1
    assert len(diff.removed) == 0


def test_watch_detects_removed_entry(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    entries = [_entry("root", "* * * * *", "/a.sh"), _entry("root", "0 1 * * *", "/b.sh")]
    watcher.watch("host1", entries)
    diff = watcher.watch("host1", entries[:1])
    assert len(diff.removed) == 1
    assert diff.removed[0].command == "/b.sh"


def test_watch_no_changes(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    entries = [_entry("root", "0 0 * * *", "/nightly.sh")]
    watcher.watch("host1", entries)
    diff = watcher.watch("host1", entries)
    assert not diff.has_changes


# ---------------------------------------------------------------------------
# WatchReport
# ---------------------------------------------------------------------------

def test_watch_many_report_has_any_changes(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    host_entries = {
        "h1": [_entry("root", "* * * * *", "/x.sh", host="h1")],
        "h2": [],
    }
    report = watcher.watch_many(host_entries)
    assert isinstance(report, WatchReport)
    assert report.has_any_changes  # h1 has new entries on first run


def test_watch_report_summary_lines(tmp_path):
    watcher = ScheduleWatcher(str(tmp_path))
    report = watcher.watch_many({"h1": [], "h2": []})
    lines = report.summary_lines()
    assert len(lines) == 2
    assert all(":" in line for line in lines)
