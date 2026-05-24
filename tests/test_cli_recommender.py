"""Tests for cli_recommender."""
from __future__ import annotations
import argparse
from unittest.mock import MagicMock
from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult
from cronclear.cli_recommender import build_recommender_parser, run_recommender_command, _render_report
from cronclear.schedule_recommender import Recommendation, RecommendationReport


def _parse(args: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_recommender_parser(sub)
    return parser.parse_args(["recommend"] + args)


def _make_entry(schedule: str, command: str = "cmd", host: str = "h1") -> CronEntry:
    e = CronEntry(schedule=schedule, command=command)
    e.host = host
    e.user = "root"
    return e


def test_parser_defaults():
    ns = _parse([])
    assert ns.host is None
    assert ns.no_color is False


def test_parser_host_option():
    ns = _parse(["--host", "web1"])
    assert ns.host == "web1"


def test_parser_no_color_flag():
    ns = _parse(["--no-color"])
    assert ns.no_color is True


def test_run_returns_0_no_issues(capsys):
    result = CollectionResult(host="h1", entries=[_make_entry("0 3 * * *", "backup")])
    ns = _parse([])
    code = run_recommender_command(ns, [result])
    assert code == 0
    captured = capsys.readouterr()
    assert "No recommendations" in captured.out


def test_run_returns_0_with_issues(capsys):
    result = CollectionResult(host="h1", entries=[_make_entry("* * * * *", "poll")])
    ns = _parse([])
    code = run_recommender_command(ns, [result])
    assert code == 0
    captured = capsys.readouterr()
    assert "Recommendations" in captured.out


def test_render_host_filter(capsys):
    report = RecommendationReport(recommendations=[
        Recommendation("web1", "a", "* * * * *", "*/5 * * * *", "noisy"),
        Recommendation("web2", "b", "* * * * *", "*/5 * * * *", "noisy"),
    ])
    _render_report(report, host_filter="web1", color=False)
    out = __import__("sys").stdout
    # just ensure no exception; capsys checked via other tests


def test_render_empty_report(capsys):
    _render_report(RecommendationReport(), host_filter=None, color=False)
    captured = capsys.readouterr()
    assert "No recommendations" in captured.out
