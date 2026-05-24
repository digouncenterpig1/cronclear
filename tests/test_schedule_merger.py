"""Tests for schedule_merger module."""

import pytest
from cronclear.schedule_merger import (
    _job_key,
    MergedJob,
    merge_results,
)
from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult
from cronclear.cron_parser import ParseResult


def _entry(schedule: str, command: str, user: str = "root", host: str = "host1") -> CronEntry:
    e = CronEntry(
        schedule=schedule,
        command=command,
        raw=f"{schedule} {command}",
        user=user,
        host=host,
    )
    return e


def _result(host: str, entries: list) -> CollectionResult:
    parse = ParseResult(entries=entries, errors=[])
    return CollectionResult(host=host, parse_result=parse, error=None)


# ---------------------------------------------------------------------------
# _job_key
# ---------------------------------------------------------------------------

def test_job_key_uses_schedule_and_command():
    e = _entry("0 * * * *", "/usr/bin/backup")
    assert _job_key(e) == ("0 * * * *", "/usr/bin/backup")


def test_job_key_strips_extra_whitespace():
    e = _entry("0 * * * *", "  /usr/bin/backup  ")
    assert _job_key(e) == ("0 * * * *", "/usr/bin/backup")


# ---------------------------------------------------------------------------
# MergedJob
# ---------------------------------------------------------------------------

def test_merged_job_host_count():
    e1 = _entry("0 * * * *", "/bin/job", host="h1")
    e2 = _entry("0 * * * *", "/bin/job", host="h2")
    job = MergedJob(schedule="0 * * * *", command="/bin/job", entries=[e1, e2])
    assert job.host_count == 2


def test_merged_job_is_shared_true():
    e1 = _entry("0 * * * *", "/bin/job", host="h1")
    e2 = _entry("0 * * * *", "/bin/job", host="h2")
    job = MergedJob(schedule="0 * * * *", command="/bin/job", entries=[e1, e2])
    assert job.is_shared is True


def test_merged_job_is_shared_false():
    e1 = _entry("0 * * * *", "/bin/job", host="h1")
    job = MergedJob(schedule="0 * * * *", command="/bin/job", entries=[e1])
    assert job.is_shared is False


def test_merged_job_to_dict():
    e1 = _entry("0 * * * *", "/bin/job", host="h1")
    e2 = _entry("0 * * * *", "/bin/job", host="h2")
    job = MergedJob(schedule="0 * * * *", command="/bin/job", entries=[e1, e2])
    d = job.to_dict()
    assert d["schedule"] == "0 * * * *"
    assert d["command"] == "/bin/job"
    assert d["host_count"] == 2
    assert set(d["hosts"]) == {"h1", "h2"}
    assert d["is_shared"] is True


def test_merged_job_hosts_property():
    e1 = _entry("0 * * * *", "/bin/job", host="alpha")
    e2 = _entry("0 * * * *", "/bin/job", host="beta")
    job = MergedJob(schedule="0 * * * *", command="/bin/job", entries=[e1, e2])
    assert job.hosts == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# merge_results
# ---------------------------------------------------------------------------

def test_merge_results_empty():
    report = merge_results([])
    assert report.total == 0
    assert report.jobs == []


def test_merge_results_single_host():
    entries = [
        _entry("0 * * * *", "/bin/a", host="h1"),
        _entry("30 2 * * *", "/bin/b", host="h1"),
    ]
    result = _result("h1", entries)
    report = merge_results([result])
    assert report.total == 2
    assert all(not j.is_shared for j in report.jobs)


def test_merge_results_shared_job_across_hosts():
    e1 = _entry("0 * * * *", "/bin/shared", host="h1")
    e2 = _entry("0 * * * *", "/bin/shared", host="h2")
    r1 = _result("h1", [e1])
    r2 = _result("h2", [e2])
    report = merge_results([r1, r2])
    assert report.total == 1
    shared = report.jobs[0]
    assert shared.is_shared is True
    assert shared.host_count == 2


def test_merge_results_unique_per_host():
    e1 = _entry("0 * * * *", "/bin/a", host="h1")
    e2 = _entry("0 * * * *", "/bin/b", host="h2")
    r1 = _result("h1", [e1])
    r2 = _result("h2", [e2])
    report = merge_results([r1, r2])
    assert report.total == 2
    assert all(not j.is_shared for j in report.jobs)


def test_merge_results_shared_count():
    e1 = _entry("0 * * * *", "/bin/shared", host="h1")
    e2 = _entry("0 * * * *", "/bin/shared", host="h2")
    e3 = _entry("5 4 * * *", "/bin/unique", host="h1")
    r1 = _result("h1", [e1, e3])
    r2 = _result("h2", [e2])
    report = merge_results([r1, r2])
    assert report.shared_count == 1
    assert report.unique_count == 1


def test_merge_results_skips_failed_hosts():
    e1 = _entry("0 * * * *", "/bin/a", host="h1")
    good = _result("h1", [e1])
    bad = CollectionResult(host="h2", parse_result=None, error="connection refused")
    report = merge_results([good, bad])
    assert report.total == 1
