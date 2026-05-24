"""Tests for cronclear.schedule_silencer."""

import json
import pytest
from pathlib import Path

from cronclear.schedule_silencer import (
    SilenceRule,
    SilenceReport,
    apply_silence,
    load_rules,
    save_rules,
    matching_rule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeEntry:
    """Minimal stand-in for CronEntry."""
    def __init__(self, command: str, host: str = "host1"):
        self.command = command
        self.host = host
        self.user = "root"

    @property
    def schedule(self):
        return "* * * * *"

    def __str__(self):
        return f"{self.schedule} {self.command}"


def _e(cmd, host="web-01"):
    return _FakeEntry(cmd, host)


# ---------------------------------------------------------------------------
# SilenceRule.matches
# ---------------------------------------------------------------------------

def test_rule_matches_exact_host_and_command():
    rule = SilenceRule(host_pattern="web-01", command_pattern="*/backup.sh")
    assert rule.matches(_e("*/backup.sh", "web-01"))


def test_rule_glob_host():
    rule = SilenceRule(host_pattern="web-*", command_pattern="*backup*")
    assert rule.matches(_e("/usr/local/bin/backup.sh", "web-99"))
    assert not rule.matches(_e("/usr/local/bin/backup.sh", "db-01"))


def test_rule_wildcard_matches_all():
    rule = SilenceRule(host_pattern="*", command_pattern="*")
    assert rule.matches(_e("/any/command", "any-host"))


def test_rule_no_match_command():
    rule = SilenceRule(host_pattern="*", command_pattern="*/cleanup.sh")
    assert not rule.matches(_e("/other/script.sh"))


# ---------------------------------------------------------------------------
# apply_silence
# ---------------------------------------------------------------------------

def test_apply_silence_no_rules_keeps_all():
    entries = [_e("/a.sh"), _e("/b.sh")]
    report = apply_silence(entries, [])
    assert len(report.kept) == 2
    assert report.total_silenced == 0


def test_apply_silence_silences_matching():
    rules = [SilenceRule(command_pattern="*/noisy.sh")]
    entries = [_e("/noisy.sh"), _e("/important.sh")]
    report = apply_silence(entries, rules)
    assert len(report.kept) == 1
    assert report.kept[0].command == "/important.sh"
    assert report.total_silenced == 1


def test_apply_silence_multiple_rules():
    rules = [
        SilenceRule(command_pattern="*/a.sh"),
        SilenceRule(command_pattern="*/b.sh"),
    ]
    entries = [_e("/a.sh"), _e("/b.sh"), _e("/c.sh")]
    report = apply_silence(entries, rules)
    assert report.total_silenced == 2
    assert len(report.kept) == 1


# ---------------------------------------------------------------------------
# matching_rule
# ---------------------------------------------------------------------------

def test_matching_rule_returns_first_match():
    r1 = SilenceRule(command_pattern="*/a.sh", reason="first")
    r2 = SilenceRule(command_pattern="*/a.sh", reason="second")
    result = matching_rule(_e("/a.sh"), [r1, r2])
    assert result is r1


def test_matching_rule_returns_none_when_no_match():
    rule = SilenceRule(command_pattern="*/x.sh")
    assert matching_rule(_e("/y.sh"), [rule]) is None


# ---------------------------------------------------------------------------
# save / load rules
# ---------------------------------------------------------------------------

def test_save_and_load_rules(tmp_path):
    path = tmp_path / "silence.json"
    rules = [
        SilenceRule(host_pattern="web-*", command_pattern="*/backup.sh", reason="noisy"),
        SilenceRule(host_pattern="*", command_pattern="*/healthcheck*"),
    ]
    save_rules(rules, path)
    loaded = load_rules(path)
    assert len(loaded) == 2
    assert loaded[0].host_pattern == "web-*"
    assert loaded[1].reason == ""


def test_load_rules_missing_file_returns_empty(tmp_path):
    result = load_rules(tmp_path / "nonexistent.json")
    assert result == []


def test_saved_json_structure(tmp_path):
    path = tmp_path / "silence.json"
    save_rules([SilenceRule(reason="test")], path)
    data = json.loads(path.read_text())
    assert "rules" in data
    assert data["rules"][0]["reason"] == "test"
