"""Tests for schedule_archiver module."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cronclear.schedule_archiver import (
    ArchiveEntry,
    ArchiveReport,
    archive_results,
    load_archive,
)


def _make_entry(schedule: str, command: str, user: str = "root") -> MagicMock:
    e = MagicMock()
    e.schedule = schedule
    e.user = user
    e.__str__ = lambda self: command
    return e


def _make_result(host: str, entries):
    r = MagicMock()
    r.host = host
    r.entries = entries
    return r


def test_archive_entry_round_trip():
    ae = ArchiveEntry(
        timestamp="2024-01-01T00:00:00+00:00",
        host="web-01",
        user="deploy",
        schedule="0 * * * *",
        command="/usr/bin/backup.sh",
    )
    restored = ArchiveEntry.from_dict(ae.to_dict())
    assert restored.host == ae.host
    assert restored.user == ae.user
    assert restored.schedule == ae.schedule
    assert restored.command == ae.command
    assert restored.timestamp == ae.timestamp


def test_archive_results_creates_file(tmp_path):
    entry = _make_entry("0 2 * * *", "/opt/cleanup.sh")
    result = _make_result("db-01", [entry])

    report = archive_results([result], tmp_path, timestamp="2024-06-01T12:00:00+00:00")

    assert isinstance(report, ArchiveReport)
    assert report.path.exists()
    assert report.entry_count == 1
    assert "db-01" in report.hosts


def test_archive_results_json_structure(tmp_path):
    e1 = _make_entry("*/5 * * * *", "/bin/check.sh", user="cron")
    e2 = _make_entry("@daily", "/bin/rotate.sh", user="root")
    r = _make_result("app-01", [e1, e2])

    report = archive_results([r], tmp_path, timestamp="2024-06-01T08:00:00+00:00")
    data = json.loads(report.path.read_text())

    assert "archived_at" in data
    assert len(data["entries"]) == 2
    assert data["entries"][0]["host"] == "app-01"
    assert data["entries"][1]["schedule"] == "@daily"


def test_archive_results_multiple_hosts(tmp_path):
    r1 = _make_result("host-a", [_make_entry("0 1 * * *", "/a.sh")])
    r2 = _make_result("host-b", [_make_entry("0 2 * * *", "/b.sh")])

    report = archive_results([r1, r2], tmp_path)

    assert report.entry_count == 2
    assert set(report.hosts) == {"host-a", "host-b"}


def test_archive_results_empty(tmp_path):
    report = archive_results([], tmp_path, timestamp="2024-01-01T00:00:00+00:00")
    assert report.entry_count == 0
    assert report.path.exists()


def test_load_archive_round_trip(tmp_path):
    entry = _make_entry("30 6 * * 1", "/usr/bin/weekly.sh", user="ops")
    result = _make_result("srv-01", [entry])

    report = archive_results([result], tmp_path, timestamp="2024-07-01T06:30:00+00:00")
    loaded = load_archive(report.path)

    assert len(loaded) == 1
    assert loaded[0].host == "srv-01"
    assert loaded[0].user == "ops"
    assert loaded[0].schedule == "30 6 * * 1"


def test_archive_dir_created_if_missing(tmp_path):
    nested = tmp_path / "deep" / "nested" / "dir"
    entry = _make_entry("* * * * *", "/bin/ping.sh")
    result = _make_result("node-01", [entry])

    report = archive_results([result], nested, timestamp="2024-01-01T00:00:00+00:00")
    assert nested.exists()
    assert report.path.exists()
