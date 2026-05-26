"""Tests for cli_comparator."""
from __future__ import annotations
import argparse
import pytest
from unittest.mock import MagicMock

from cronclear.cli_comparator import (
    build_comparator_parser,
    _parse_pairs,
    _render_comparison,
    run_comparator_command,
)
from cronclear.schedule_comparator import ComparisonReport, HostComparison


def _parse(args):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_comparator_parser(sub)
    return parser.parse_args(["compare"] + args)


def test_parser_requires_pair():
    with pytest.raises(SystemExit):
        _parse([])


def test_parser_accepts_pair():
    ns = _parse(["--pair", "web1:web2"])
    assert ns.pairs == ["web1:web2"]


def test_parser_multiple_pairs():
    ns = _parse(["--pair", "a:b", "--pair", "c:d"])
    assert len(ns.pairs) == 2


def test_parser_no_color_default_false():
    ns = _parse(["--pair", "a:b"])
    assert ns.no_color is False


def test_parse_pairs_valid():
    result = _parse_pairs(["host1:host2", "a:b"])
    assert result == [("host1", "host2"), ("a", "b")]


def test_parse_pairs_invalid_skipped():
    result = _parse_pairs(["nocolon"])
    assert result == []


def test_run_returns_0_no_differences():
    comp = HostComparison(host_a="a", host_b="b", only_in_a=[], only_in_b=[])
    report = ComparisonReport(comparisons=[comp])
    ns = _parse(["--pair", "a:b"])
    assert run_comparator_command(ns, report) == 0


def test_run_returns_1_with_differences():
    e = MagicMock()
    e.schedule = "* * * * *"
    e.command = "x.sh"
    comp = HostComparison(host_a="a", host_b="b", only_in_a=[e], only_in_b=[])
    report = ComparisonReport(comparisons=[comp])
    ns = _parse(["--pair", "a:b"])
    assert run_comparator_command(ns, report) == 1


def test_run_returns_1_empty_report():
    report = ComparisonReport(comparisons=[])
    ns = _parse(["--pair", "a:b"])
    assert run_comparator_command(ns, report) == 1


def test_render_comparison_prints_diff(capsys):
    e = MagicMock()
    e.schedule = "* * * * *"
    e.command = "job.sh"
    comp = HostComparison(host_a="h1", host_b="h2", only_in_a=[e], only_in_b=[])
    _render_comparison(comp)
    out = capsys.readouterr().out
    assert "[DIFF]" in out
    assert "job.sh" in out
