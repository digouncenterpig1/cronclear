"""Tests for cronclear.cli_baseline."""
import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cronclear.cli_baseline import build_baseline_parser, run_baseline_command
from cronclear.schedule_baseline import BaselineEntry
from cronclear.cron_parser import CronEntry


def _parse(*args: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_baseline_parser(sub)
    return parser.parse_args(["baseline"] + list(args))


def _make_entry(raw: str, host: str = "h1") -> CronEntry:
    return CronEntry(raw=raw, user="root", host=host)


@patch("cronclear.cli_baseline._collect_all_entries")
def test_capture_saves_file(mock_collect, tmp_path):
    mock_collect.return_value = [_make_entry("* * * * * job")]
    out = tmp_path / "b.json"
    args = _parse("capture", "h1", "--output", str(out))
    rc = run_baseline_command(args)
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert len(data) == 1
    assert data[0]["raw"] == "* * * * * job"


@patch("cronclear.cli_baseline._collect_all_entries")
def test_capture_prints_count(mock_collect, tmp_path, capsys):
    mock_collect.return_value = [_make_entry("0 * * * * x"), _make_entry("1 * * * * y")]
    out = tmp_path / "b.json"
    args = _parse("capture", "h1", "--output", str(out))
    run_baseline_command(args)
    captured = capsys.readouterr()
    assert "2 entries" in captured.out


@patch("cronclear.cli_baseline._collect_all_entries")
def test_compare_no_baseline_returns_1(mock_collect, tmp_path, capsys):
    mock_collect.return_value = []
    args = _parse("compare", "h1", "--baseline", str(tmp_path / "missing.json"))
    rc = run_baseline_command(args)
    assert rc == 1
    assert "No baseline" in capsys.readouterr().err


@patch("cronclear.cli_baseline._collect_all_entries")
def test_compare_no_changes_returns_0(mock_collect, tmp_path):
    entry = _make_entry("0 0 * * * backup")
    baseline_path = tmp_path / "b.json"
    baseline_path.write_text(
        json.dumps([{"raw": "0 0 * * * backup", "user": "root", "host": "h1"}])
    )
    mock_collect.return_value = [entry]
    args = _parse("compare", "h1", "--baseline", str(baseline_path))
    rc = run_baseline_command(args)
    assert rc == 0


@patch("cronclear.cli_baseline._collect_all_entries")
def test_compare_changes_returns_1(mock_collect, tmp_path, capsys):
    baseline_path = tmp_path / "b.json"
    baseline_path.write_text(
        json.dumps([{"raw": "0 0 * * * old", "user": "root", "host": "h1"}])
    )
    mock_collect.return_value = [_make_entry("* * * * * new")]
    args = _parse("compare", "h1", "--baseline", str(baseline_path))
    rc = run_baseline_command(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Added" in out or "Removed" in out
