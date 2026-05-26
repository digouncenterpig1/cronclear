"""Tests for schedule_comparator."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock

from cronclear.schedule_comparator import (
    _entry_key,
    compare_hosts,
    compare_all,
    HostComparison,
    ComparisonReport,
)
from cronclear.cron_collector import CollectionResult


def _entry(schedule: str, command: str, host: str = "h1") -> MagicMock:
    e = MagicMock()
    e.schedule = schedule
    e.command = command
    e.host = host
    return e


def _result(host: str, entries) -> CollectionResult:
    return CollectionResult(host=host, entries=entries, error=None)


def test_entry_key_combines_schedule_and_command():
    e = _entry("0 * * * *", "backup.sh")
    assert _entry_key(e) == "0 * * * *|backup.sh"


def test_entry_key_strips_command_whitespace():
    e = _entry("0 * * * *", "  backup.sh  ")
    assert _entry_key(e) == "0 * * * *|backup.sh"


def test_compare_hosts_identical():
    e1 = _entry("0 * * * *", "backup.sh", "h1")
    e2 = _entry("0 * * * *", "backup.sh", "h2")
    r1 = _result("h1", [e1])
    r2 = _result("h2", [e2])
    comp = compare_hosts(r1, r2)
    assert not comp.has_differences
    assert len(comp.shared) == 1
    assert comp.only_in_a == []
    assert comp.only_in_b == []


def test_compare_hosts_only_in_a():
    e1 = _entry("0 * * * *", "job_a.sh", "h1")
    r1 = _result("h1", [e1])
    r2 = _result("h2", [])
    comp = compare_hosts(r1, r2)
    assert comp.has_differences
    assert len(comp.only_in_a) == 1
    assert comp.only_in_b == []


def test_compare_hosts_only_in_b():
    e2 = _entry("30 2 * * *", "nightly.sh", "h2")
    r1 = _result("h1", [])
    r2 = _result("h2", [e2])
    comp = compare_hosts(r1, r2)
    assert comp.has_differences
    assert comp.only_in_b == [e2]


def test_compare_hosts_mixed():
    shared = _entry("0 * * * *", "shared.sh", "h1")
    shared2 = _entry("0 * * * *", "shared.sh", "h2")
    unique_a = _entry("5 * * * *", "only_a.sh", "h1")
    unique_b = _entry("10 * * * *", "only_b.sh", "h2")
    r1 = _result("h1", [shared, unique_a])
    r2 = _result("h2", [shared2, unique_b])
    comp = compare_hosts(r1, r2)
    assert comp.has_differences
    assert comp.difference_count == 2
    assert len(comp.shared) == 1


def test_compare_all_builds_report():
    e1 = _entry("0 * * * *", "j.sh", "web1")
    e2 = _entry("0 * * * *", "j.sh", "web2")
    results = [_result("web1", [e1]), _result("web2", [e2])]
    report = compare_all(results, [("web1", "web2")])
    assert report.total_pairs == 1
    assert len(report.differing_pairs) == 0


def test_compare_all_skips_missing_hosts():
    results = [_result("web1", [])]
    report = compare_all(results, [("web1", "ghost")])
    assert report.total_pairs == 0


def test_comparison_report_differing_pairs():
    comp_same = HostComparison(host_a="a", host_b="b", only_in_a=[], only_in_b=[])
    comp_diff = HostComparison(host_a="c", host_b="d",
                               only_in_a=[_entry("* * * * *", "x")], only_in_b=[])
    report = ComparisonReport(comparisons=[comp_same, comp_diff])
    assert len(report.differing_pairs) == 1
