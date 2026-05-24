"""Tests for schedule_linter."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_linter import LintReport, LintIssue, lint_results, _lint_entry


def _entry(
    schedule: str = "0 * * * *",
    command: str = "/usr/bin/backup.sh",
    host: str = "web01",
    user: str = "root",
    is_shortcut: bool = False,
) -> CronEntry:
    e = MagicMock(spec=CronEntry)
    e.schedule = MagicMock()
    e.schedule.__str__ = lambda _: schedule
    e.command = command
    e.host = host
    e.user = user
    e.is_shortcut = is_shortcut
    return e


def _result(entries) -> CollectionResult:
    r = MagicMock(spec=CollectionResult)
    r.entries = entries
    return r


def test_no_issues_for_clean_entry():
    issues = _lint_entry(_entry())
    assert issues == []


def test_noisy_every_minute():
    issues = _lint_entry(_entry(schedule="* * * * *"))
    codes = [i.code for i in issues]
    assert "NOISY" in codes


def test_noisy_every_minute_slash_1():
    issues = _lint_entry(_entry(schedule="*/1 * * * *"))
    codes = [i.code for i in issues]
    assert "NOISY" in codes


def test_risky_rm_command():
    issues = _lint_entry(_entry(command="rm -rf /tmp/cache"))
    codes = [i.code for i in issues]
    assert "RISKY_CMD" in codes


def test_risky_chmod_777():
    issues = _lint_entry(_entry(command="chmod 777 /var/www"))
    codes = [i.code for i in issues]
    assert "RISKY_CMD" in codes


def test_empty_command():
    issues = _lint_entry(_entry(command=""))
    codes = [i.code for i in issues]
    assert "EMPTY_CMD" in codes


def test_malformed_schedule_too_few_fields():
    issues = _lint_entry(_entry(schedule="0 *", is_shortcut=False))
    codes = [i.code for i in issues]
    assert "MALFORMED" in codes


def test_shortcut_not_flagged_as_malformed():
    issues = _lint_entry(_entry(schedule="@daily", is_shortcut=True))
    codes = [i.code for i in issues]
    assert "MALFORMED" not in codes


def test_lint_issue_str():
    issue = LintIssue(
        host="h1", user="root", command="rm -rf /",
        schedule="* * * * *", code="RISKY_CMD", message="Dangerous"
    )
    assert "RISKY_CMD" in str(issue)
    assert "h1" in str(issue)


def test_lint_results_aggregates_multiple_hosts():
    entries_a = [_entry(command="rm -rf /tmp"), _entry()]
    entries_b = [_entry(schedule="* * * * *", host="db01")]
    report = lint_results([_result(entries_a), _result(entries_b)])
    assert report.total >= 2


def test_lint_report_by_code():
    entries = [_entry(schedule="* * * * *"), _entry(command="rm -rf /")]
    report = lint_results([_result(entries)])
    noisy = report.by_code("NOISY")
    assert all(i.code == "NOISY" for i in noisy)


def test_lint_report_has_issues_false_when_clean():
    report = lint_results([_result([_entry()])])
    assert not report.has_issues()


def test_lint_report_has_issues_true_when_dirty():
    report = lint_results([_result([_entry(schedule="* * * * *")])])
    assert report.has_issues()
