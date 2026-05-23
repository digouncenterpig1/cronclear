"""Tests for schedule_deduplicator module."""
from __future__ import annotations

import pytest

from cronclear.cron_parser import CronEntry, ParseResult
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_deduplicator import (
    DeduplicatedGroup,
    DeduplicationReport,
    _entry_fingerprint,
    deduplicate_entries,
)


def _entry(schedule: str, command: str, host: str = "host1", user: str = "root") -> CronEntry:
    e = CronEntry.__new__(CronEntry)
    e.schedule = schedule
    e.command = command
    e.host = host
    e.user = user
    e.raw = f"{schedule} {command}"
    return e


def _result(host: str, entries: list) -> CollectionResult:
    pr = ParseResult(entries=entries, errors=[])
    return CollectionResult(host=host, parse_results=[pr], errors=[])


def test_entry_fingerprint_uses_schedule_and_command():
    e = _entry("0 * * * *", "/usr/bin/backup")
    assert _entry_fingerprint(e) == "0 * * * *|/usr/bin/backup"


def test_entry_fingerprint_strips_command_whitespace():
    e = _entry("0 * * * *", "  /usr/bin/backup  ")
    assert _entry_fingerprint(e) == "0 * * * *|/usr/bin/backup"


def test_deduplicate_no_duplicates():
    r1 = _result("host1", [_entry("0 1 * * *", "/bin/job1", host="host1")])
    r2 = _result("host2", [_entry("0 2 * * *", "/bin/job2", host="host2")])
    report = deduplicate_entries([r1, r2])
    assert len(report.duplicate_groups) == 0
    assert len(report.unique_groups) == 2
    assert report.redundant_entry_count == 0


def test_deduplicate_detects_duplicate_across_hosts():
    e1 = _entry("0 3 * * *", "/bin/sync", host="host1")
    e2 = _entry("0 3 * * *", "/bin/sync", host="host2")
    r1 = _result("host1", [e1])
    r2 = _result("host2", [e2])
    report = deduplicate_entries([r1, r2])
    assert len(report.duplicate_groups) == 1
    grp = report.duplicate_groups[0]
    assert set(grp.hosts) == {"host1", "host2"}
    assert report.redundant_entry_count == 1


def test_deduplicate_total_entries():
    entries = [
        _entry("* * * * *", "/bin/a", host="h1"),
        _entry("* * * * *", "/bin/a", host="h2"),
        _entry("0 0 * * *", "/bin/b", host="h1"),
    ]
    r = _result("mixed", entries)
    report = deduplicate_entries([r])
    assert report.total_entries == 3


def test_deduplicate_group_properties():
    e1 = _entry("5 4 * * *", "/opt/run.sh", host="alpha")
    e2 = _entry("5 4 * * *", "/opt/run.sh", host="beta")
    r = _result("multi", [e1, e2])
    report = deduplicate_entries([r])
    grp = report.duplicate_groups[0]
    assert grp.command == "/opt/run.sh"
    assert grp.schedule == "5 4 * * *"
    assert grp.is_duplicate is True


def test_deduplicate_empty_results():
    report = deduplicate_entries([])
    assert report.total_entries == 0
    assert report.duplicate_groups == []
    assert report.unique_groups == []


def test_unique_group_is_not_duplicate():
    e = _entry("0 6 * * 1", "/bin/weekly", host="solo")
    r = _result("solo", [e])
    report = deduplicate_entries([r])
    assert len(report.unique_groups) == 1
    assert report.unique_groups[0].is_duplicate is False
