"""Tests for schedule_recommender."""
from __future__ import annotations
import pytest
from cronclear.cron_parser import CronEntry
from cronclear.schedule_recommender import recommend, Recommendation, RecommendationReport


def _entry(schedule: str, command: str = "cmd", host: str = "h1") -> CronEntry:
    e = CronEntry(schedule=schedule, command=command)
    e.host = host
    e.user = "root"
    return e


def test_recommend_returns_report():
    entries = [_entry("*/5 * * * *", "backup")]
    report = recommend(entries)
    assert isinstance(report, RecommendationReport)


def test_every_minute_gets_recommendation():
    entries = [_entry("* * * * *", "poll")]
    report = recommend(entries)
    assert report.total == 1
    assert report.recommendations[0].suggested_schedule == "*/5 * * * *"


def test_every_minute_alt_gets_recommendation():
    entries = [_entry("*/1 * * * *", "poll")]
    report = recommend(entries)
    assert report.total == 1
    assert "every-minute" in report.recommendations[0].reason


def test_clean_schedule_no_recommendation():
    entries = [_entry("0 3 * * *", "nightly_backup")]
    report = recommend(entries)
    assert report.total == 0


def test_high_risk_schedule_suggests_off_peak():
    # */2 every hour is high-frequency => score >= 8
    entries = [_entry("*/2 * * * *", "heavy_job")]
    report = recommend(entries)
    assert report.total >= 1


def test_by_host_filters_correctly():
    entries = [
        _entry("* * * * *", "poll", host="web1"),
        _entry("* * * * *", "poll", host="web2"),
    ]
    report = recommend(entries)
    assert len(report.by_host("web1")) == 1
    assert len(report.by_host("web2")) == 1
    assert len(report.by_host("db1")) == 0


def test_shortcut_entries_are_skipped():
    e = _entry("@daily", "cleanup")
    report = recommend([e])
    assert report.total == 0


def test_recommendation_str():
    rec = Recommendation(
        host="h1",
        command="cmd",
        current_schedule="* * * * *",
        suggested_schedule="*/5 * * * *",
        reason="too noisy",
    )
    s = str(rec)
    assert "h1" in s
    assert "*/5 * * * *" in s
    assert "too noisy" in s


def test_multiple_entries_mixed():
    entries = [
        _entry("0 2 * * *", "safe_job"),
        _entry("* * * * *", "noisy"),
        _entry("0 4 * * 0", "weekly"),
    ]
    report = recommend(entries)
    assert report.total == 1
    assert report.recommendations[0].command == "noisy"
