"""Tests for schedule_search module."""
from __future__ import annotations

import pytest

from cronclear.cron_parser import CronEntry, ParseResult
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_search import SearchReport, SearchResult, search_entries


def _entry(command: str, schedule: str = "0 * * * *", user: str = "root") -> CronEntry:
    e = CronEntry(raw=f"{schedule} {command}")
    e._schedule = schedule
    e._command = command
    e._user = user
    # Patch attributes directly for simplicity
    object.__setattr__(e, "command", command)
    object.__setattr__(e, "user", user)
    return e


class _FakeEntry:
    """Minimal stand-in for CronEntry."""
    def __init__(self, command, schedule_str="0 * * * *", user="root"):
        self.command = command
        self.user = user
        self._sched = schedule_str

    def __str__(self):
        return f"{self._sched} {self.command}"

    @property
    def schedule(self):
        class _S:
            def __init__(self, s):
                self._s = s
            def __str__(self):
                return self._s
        return _S(self._sched)


def _make_result(host: str, entries) -> CollectionResult:
    pr = ParseResult(entries=entries, errors=[])
    return CollectionResult(host=host, parse_result=pr, error=None)


def _fake(cmd, sched="0 * * * *", user="root"):
    return _FakeEntry(cmd, sched, user)


def test_search_finds_by_command():
    entries = [_fake("/usr/bin/backup"), _fake("/usr/bin/cleanup")]
    results = [_make_result("host1", entries)]
    report = search_entries(results, "backup")
    assert report.total == 1
    assert report.results[0].matched_field == "command"
    assert report.results[0].host == "host1"


def test_search_finds_by_schedule():
    entries = [_fake("/bin/foo", sched="*/5 * * * *")]
    results = [_make_result("host1", entries)]
    report = search_entries(results, r"\*/5", field="schedule")
    assert report.total == 1
    assert report.results[0].matched_field == "schedule"


def test_search_finds_by_user():
    entries = [_fake("/bin/bar", user="deploy"), _fake("/bin/baz", user="root")]
    results = [_make_result("host2", entries)]
    report = search_entries(results, "deploy", field="user")
    assert report.total == 1
    assert report.results[0].entry.user == "deploy"


def test_search_case_insensitive_default():
    entries = [_fake("/usr/bin/BACKUP")]
    results = [_make_result("h", entries)]
    report = search_entries(results, "backup")
    assert report.total == 1


def test_search_case_sensitive_no_match():
    entries = [_fake("/usr/bin/BACKUP")]
    results = [_make_result("h", entries)]
    report = search_entries(results, "backup", case_sensitive=True)
    assert report.total == 0


def test_search_no_match_returns_empty_report():
    entries = [_fake("/bin/nothing")]
    results = [_make_result("h", entries)]
    report = search_entries(results, "zzznomatch")
    assert report.total == 0
    assert report.hosts == []


def test_search_invalid_pattern_raises():
    results = [_make_result("h", [])]
    with pytest.raises(ValueError, match="Invalid search pattern"):
        search_entries(results, "[invalid")


def test_search_multiple_hosts():
    r1 = _make_result("host-a", [_fake("/bin/sync")])
    r2 = _make_result("host-b", [_fake("/bin/sync")])
    report = search_entries([r1, r2], "sync")
    assert report.total == 2
    assert sorted(report.hosts) == ["host-a", "host-b"]
