"""Tests for schedule_templater_cli."""
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cronclear.schedule_templater_cli import (
    _load_templates,
    _render_report,
    build_templater_parser,
    run_templater_command,
)
from cronclear.schedule_templater import TemplateReport, TemplateMatch, ScheduleTemplate


def _parse(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    build_templater_parser(sub)
    return parser.parse_args(args)


def _make_entry(schedule: str = "0 * * * *", host: str = "web1", cmd: str = "/bin/job"):
    e = MagicMock()
    e.schedule = schedule
    e.host = host
    e.__str__ = lambda self: f"{self.schedule} {cmd}"
    return e


def _make_report(matched=1, unmatched=0):
    matches = [TemplateMatch(label="nightly", entry=_make_entry()) for _ in range(matched)]
    unmatched_entries = [_make_entry(host="db1") for _ in range(unmatched)]
    return TemplateReport(matches=matches, unmatched=unmatched_entries)


# --- parser tests ---

def test_parser_requires_templates_file():
    with pytest.raises(SystemExit):
        _parse(["template"])


def test_parser_accepts_templates_file():
    ns = _parse(["template", "templates.json"])
    assert ns.templates_file == "templates.json"


def test_parser_host_option_appends():
    ns = _parse(["template", "t.json", "--host", "web1", "--host", "web2"])
    assert ns.hosts == ["web1", "web2"]


def test_parser_unmatched_flag():
    ns = _parse(["template", "t.json", "--unmatched"])
    assert ns.unmatched is True


def test_parser_no_color_flag():
    ns = _parse(["template", "t.json", "--no-color"])
    assert ns.no_color is True


# --- _load_templates tests ---

def test_load_templates_valid(tmp_path: Path):
    data = [{"name": "nightly", "pattern": "0 2 * * *", "description": "Runs at 2am"}]
    f = tmp_path / "templates.json"
    f.write_text(json.dumps(data))
    templates = _load_templates(str(f))
    assert len(templates) == 1
    assert templates[0].name == "nightly"


def test_load_templates_missing_file():
    with pytest.raises(FileNotFoundError):
        _load_templates("/nonexistent/path/templates.json")


def test_load_templates_invalid_json(tmp_path: Path):
    f = tmp_path / "bad.json"
    f.write_text("not json")
    with pytest.raises(json.JSONDecodeError):
        _load_templates(str(f))


# --- run_templater_command tests ---

def test_run_returns_0_with_matches(capsys):
    ns = SimpleNamespace(unmatched=False, no_color=True)
    report = _make_report(matched=2, unmatched=0)
    rc = run_templater_command(ns, report=report)
    assert rc == 0
    out = capsys.readouterr().out
    assert "Template matches: 2" in out


def test_run_returns_0_with_no_entries(capsys):
    ns = SimpleNamespace(unmatched=False, no_color=True)
    report = _make_report(matched=0, unmatched=0)
    rc = run_templater_command(ns, report=report)
    assert rc == 0


def test_run_unmatched_only_shows_unmatched(capsys):
    ns = SimpleNamespace(unmatched=True, no_color=True)
    report = _make_report(matched=1, unmatched=2)
    run_templater_command(ns, report=report)
    out = capsys.readouterr().out
    assert "Unmatched entries: 2" in out


def test_run_bad_templates_file_returns_1(tmp_path: Path):
    ns = SimpleNamespace(templates_file=str(tmp_path / "missing.json"),
                         unmatched=False, no_color=True, hosts=[])
    rc = run_templater_command(ns)
    assert rc == 1
