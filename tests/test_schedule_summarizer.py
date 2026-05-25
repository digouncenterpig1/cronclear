"""Tests for schedule_summarizer and cli_summarizer."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock

import pytest

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_summarizer import HostSummary, summarize_results
from cronclear.cli_summarizer import run_summarizer_command, _render_report


def _entry(schedule: str, command: str, host: str = "h1") -> MagicMock:
    e = MagicMock()
    e.schedule = schedule
    e.__str__ = lambda self: command
    return e


def _result(host: str, entries=None, error: str | None = None) -> CollectionResult:
    return CollectionResult(host=host, entries=entries or [], error=error)


def test_summarize_single_host():
    entries = [
        _entry("0 * * * *", "/bin/a"),
        _entry("0 * * * *", "/bin/b"),
        _entry("0 0 * * *", "/bin/c"),
    ]
    result = _result("web01", entries)
    report = summarize_results([result])

    assert report.total_hosts == 1
    assert report.total_jobs == 3
    assert report.global_unique_schedules == 2
    assert report.average_jobs_per_host == pytest.approx(3.0)


def test_summarize_most_common_schedule():
    entries = [
        _entry("0 * * * *", "/bin/a"),
        _entry("0 * * * *", "/bin/b"),
        _entry("0 0 * * *", "/bin/c"),
    ]
    report = summarize_results([_result("web01", entries)])
    assert report.host_summaries[0].most_common_schedule == "0 * * * *"


def test_summarize_skips_error_results():
    good = _result("web01", [_entry("* * * * *", "/bin/x")])
    bad = _result("web02", error="connection refused")
    report = summarize_results([good, bad])
    assert report.total_hosts == 1


def test_summarize_skips_empty_entries():
    report = summarize_results([_result("web01", [])])
    assert report.total_hosts == 0
    assert report.total_jobs == 0


def test_summarize_multiple_hosts():
    r1 = _result("h1", [_entry("0 * * * *", "/a"), _entry("0 * * * *", "/b")])
    r2 = _result("h2", [_entry("0 0 * * *", "/c")])
    report = summarize_results([r1, r2])
    assert report.total_hosts == 2
    assert report.total_jobs == 3
    assert report.average_jobs_per_host == pytest.approx(1.5)


def test_host_summary_to_dict():
    hs = HostSummary(
        host="web01",
        total_jobs=2,
        unique_schedules=1,
        most_common_schedule="0 * * * *",
        commands=["/bin/a", "/bin/b"],
    )
    d = hs.to_dict()
    assert d["host"] == "web01"
    assert d["total_jobs"] == 2
    assert d["most_common_schedule"] == "0 * * * *"


def test_run_summarizer_command_returns_0(capsys):
    entries = [_entry("0 * * * *", "/bin/a")]
    results = [_result("web01", entries)]
    args = argparse.Namespace(min_jobs=0, no_color=True)
    rc = run_summarizer_command(args, results)
    assert rc == 0
    out = capsys.readouterr().out
    assert "web01" in out


def test_run_summarizer_min_jobs_filters(capsys):
    r1 = _result("h1", [_entry("* * * * *", "/a"), _entry("* * * * *", "/b")])
    r2 = _result("h2", [_entry("* * * * *", "/c")])
    args = argparse.Namespace(min_jobs=2, no_color=True)
    rc = run_summarizer_command(args, [r1, r2])
    assert rc == 0
    out = capsys.readouterr().out
    assert "h1" in out
    assert "h2" not in out


def test_run_summarizer_no_hosts_message(capsys):
    args = argparse.Namespace(min_jobs=0, no_color=True)
    rc = run_summarizer_command(args, [])
    assert rc == 0
    out = capsys.readouterr().out
    assert "No hosts" in out
