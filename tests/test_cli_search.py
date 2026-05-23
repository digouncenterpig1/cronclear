"""Tests for cli_search module."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest

from cronclear.cli_search import build_search_parser, run_search_command, _render_search
from cronclear.schedule_search import SearchReport, SearchResult


def _parse(args_list):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_search_parser(sub)
    return parser.parse_args(args_list)


def test_parser_defaults():
    ns = _parse(["search", "backup"])
    assert ns.query == "backup"
    assert ns.field is None
    assert ns.case_sensitive is False


def test_parser_field_option():
    ns = _parse(["search", "root", "--field", "user"])
    assert ns.field == "user"


def test_parser_case_sensitive_flag():
    ns = _parse(["search", "foo", "--case-sensitive"])
    assert ns.case_sensitive is True


def test_run_search_command_returns_0_on_match(capsys):
    ns = _parse(["search", "backup"])
    fake_entry = MagicMock()
    fake_entry.command = "/bin/backup"
    fake_entry.user = "root"
    fake_entry.schedule.__str__ = lambda s: "0 * * * *"
    sr = SearchResult(entry=fake_entry, host="h1", matched_field="command")
    report = SearchReport(query="backup", results=[sr])

    with patch("cronclear.cli_search.search_entries", return_value=report):
        code = run_search_command(ns, [])

    assert code == 0
    captured = capsys.readouterr()
    assert "1 match" in captured.out


def test_run_search_command_no_matches(capsys):
    ns = _parse(["search", "zzz"])
    report = SearchReport(query="zzz", results=[])

    with patch("cronclear.cli_search.search_entries", return_value=report):
        code = run_search_command(ns, [])

    assert code == 0
    captured = capsys.readouterr()
    assert "No matches" in captured.out


def test_run_search_command_invalid_pattern_returns_1(capsys):
    ns = _parse(["search", "[bad"])

    with patch(
        "cronclear.cli_search.search_entries",
        side_effect=ValueError("Invalid search pattern"),
    ):
        code = run_search_command(ns, [])

    assert code == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err
