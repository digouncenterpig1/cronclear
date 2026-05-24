"""Tests for cli_snapshot_diff module."""
from __future__ import annotations

import argparse
import pytest
from unittest.mock import MagicMock, patch

from cronclear.cli_snapshot_diff import (
    build_snapshot_diff_parser,
    run_snapshot_diff_command,
    _render_report,
)
from cronclear.schedule_snapshot_diff import SnapshotDiffReport


def _parse(args):
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_snapshot_diff_parser(sub)
    return parser.parse_args(["snapshot-diff"] + args)


def test_parser_requires_two_paths():
    ns = _parse(["old.json", "new.json"])
    assert ns.old_snapshot == "old.json"
    assert ns.new_snapshot == "new.json"


def test_parser_no_color_flag():
    ns = _parse(["old.json", "new.json", "--no-color"])
    assert ns.no_color is True


def test_run_returns_1_when_new_snap_missing():
    ns = _parse(["old.json", "new.json"])
    with patch("cronclear.cli_snapshot_diff.load_snapshot", return_value=None):
        result = run_snapshot_diff_command(ns)
    assert result == 1


def test_run_returns_0_when_no_changes(capsys):
    ns = _parse(["old.json", "new.json"])
    mock_snap = MagicMock()
    mock_report = MagicMock(spec=SnapshotDiffReport)
    mock_report.has_any_changes = False
    with patch("cronclear.cli_snapshot_diff.load_snapshot", return_value=mock_snap), \
         patch("cronclear.cli_snapshot_diff.diff_snapshots", return_value=mock_report):
        result = run_snapshot_diff_command(ns)
    assert result == 0


def test_run_returns_2_when_changes(capsys):
    ns = _parse(["old.json", "new.json"])
    mock_snap = MagicMock()
    mock_report = MagicMock(spec=SnapshotDiffReport)
    mock_report.has_any_changes = True
    mock_report.summary_lines.return_value = ["[~] h1: 1 added, 0 removed"]
    mock_report.total_added = 1
    mock_report.total_removed = 0
    mock_report.hosts_added = []
    mock_report.hosts_removed = []
    with patch("cronclear.cli_snapshot_diff.load_snapshot", return_value=mock_snap), \
         patch("cronclear.cli_snapshot_diff.diff_snapshots", return_value=mock_report):
        result = run_snapshot_diff_command(ns)
    assert result == 2


def test_render_report_no_changes(capsys):
    report = MagicMock(spec=SnapshotDiffReport)
    report.has_any_changes = False
    _render_report(report, color=False)
    captured = capsys.readouterr()
    assert "No changes" in captured.out


def test_render_report_with_changes_no_color(capsys):
    report = MagicMock(spec=SnapshotDiffReport)
    report.has_any_changes = True
    report.summary_lines.return_value = ["[+host] newhost", "[-host] oldhost"]
    report.total_added = 0
    report.total_removed = 0
    report.hosts_added = ["newhost"]
    report.hosts_removed = ["oldhost"]
    _render_report(report, color=False)
    captured = capsys.readouterr()
    assert "[+host] newhost" in captured.out
    assert "[-host] oldhost" in captured.out
