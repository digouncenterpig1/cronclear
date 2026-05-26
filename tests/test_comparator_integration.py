"""Integration tests for schedule comparator end-to-end."""
from __future__ import annotations
from unittest.mock import MagicMock

from cronclear.schedule_comparator import compare_all
from cronclear.cron_collector import CollectionResult


def _e(schedule: str, command: str, host: str = "h") -> MagicMock:
    m = MagicMock()
    m.schedule = schedule
    m.command = command
    m.host = host
    return m


def _r(host: str, *entries) -> CollectionResult:
    return CollectionResult(host=host, entries=list(entries), error=None)


def test_integration_identical_hosts():
    r1 = _r("prod1", _e("0 * * * *", "sync.sh", "prod1"))
    r2 = _r("prod2", _e("0 * * * *", "sync.sh", "prod2"))
    report = compare_all([r1, r2], [("prod1", "prod2")])
    assert report.total_pairs == 1
    assert len(report.differing_pairs) == 0


def test_integration_diverged_hosts():
    r1 = _r("prod1",
            _e("0 * * * *", "shared.sh", "prod1"),
            _e("5 0 * * *", "extra.sh", "prod1"))
    r2 = _r("prod2",
            _e("0 * * * *", "shared.sh", "prod2"))
    report = compare_all([r1, r2], [("prod1", "prod2")])
    assert len(report.differing_pairs) == 1
    assert report.differing_pairs[0].difference_count == 1


def test_integration_multiple_pairs():
    r1 = _r("a", _e("* * * * *", "j.sh", "a"))
    r2 = _r("b", _e("* * * * *", "j.sh", "b"))
    r3 = _r("c", _e("0 0 * * *", "nightly.sh", "c"))
    r4 = _r("d", _e("0 0 * * *", "nightly.sh", "d"))
    report = compare_all([r1, r2, r3, r4], [("a", "b"), ("c", "d")])
    assert report.total_pairs == 2
    assert len(report.differing_pairs) == 0


def test_integration_empty_both_hosts():
    r1 = _r("x")
    r2 = _r("y")
    report = compare_all([r1, r2], [("x", "y")])
    assert report.total_pairs == 1
    assert len(report.differing_pairs) == 0
