"""Tests for schedule_analyzer module."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from cronclear.schedule_analyzer import analyze, AnalysisReport, ScheduleSummary
from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


def _make_entry(command: str, schedule: str = "* * * * *", user: str = "root", host: str = "host1") -> CronEntry:
    e = CronEntry(schedule=schedule, command=command)
    e.user = user
    e.host = host
    return e


def _make_result(host: str, entries: list) -> CollectionResult:
    return CollectionResult(host=host, entries=entries, errors=[])


def test_analyze_returns_report():
    entry = _make_entry("/usr/bin/backup.sh", "0 2 * * *")
    result = _make_result("host1", [entry])
    report = analyze([result])
    assert isinstance(report, AnalysisReport)
    assert report.total_jobs == 1


def test_analyze_summary_fields():
    entry = _make_entry("/usr/bin/backup.sh", "0 2 * * *", user="deploy", host="web1")
    result = _make_result("web1", [entry])
    report = analyze([result])
    s = report.summaries[0]
    assert s.host == "web1"
    assert s.user == "deploy"
    assert s.command == "/usr/bin/backup.sh"
    assert s.schedule == "0 2 * * *"


def test_analyze_detects_duplicates():
    e1 = _make_entry("/usr/bin/sync.sh", "*/5 * * * *", host="host1")
    e2 = _make_entry("/usr/bin/sync.sh", "*/5 * * * *", host="host2")
    report = analyze([_make_result("host1", [e1]), _make_result("host2", [e2])])
    assert "/usr/bin/sync.sh" in report.duplicates
    assert len(report.duplicates["/usr/bin/sync.sh"]) == 2


def test_analyze_no_duplicates_for_unique_commands():
    e1 = _make_entry("/usr/bin/job_a.sh", "0 1 * * *")
    e2 = _make_entry("/usr/bin/job_b.sh", "0 2 * * *")
    report = analyze([_make_result("host1", [e1, e2])])
    assert len(report.duplicates) == 0


def test_analyze_frequent_jobs_flagged():
    # every minute = 1440/day
    entry = _make_entry("/usr/bin/poll.sh", "* * * * *")
    result = _make_result("host1", [entry])
    report = analyze([result])
    assert len(report.frequent_jobs) == 1
    assert report.summaries[0].is_frequent is True


def test_analyze_non_frequent_job():
    entry = _make_entry("/usr/bin/daily.sh", "0 3 * * *")
    result = _make_result("host1", [entry])
    report = analyze([result])
    assert len(report.frequent_jobs) == 0
    assert report.summaries[0].is_frequent is False


def test_analyze_next_run_is_datetime():
    entry = _make_entry("/usr/bin/task.sh", "0 12 * * *")
    result = _make_result("host1", [entry])
    report = analyze([result])
    assert report.summaries[0].next_run is None or isinstance(report.summaries[0].next_run, datetime)


def test_analyze_empty_results():
    report = analyze([])
    assert report.total_jobs == 0
    assert report.duplicates == {}
    assert report.frequent_jobs == []
