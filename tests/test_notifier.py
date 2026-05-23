"""Tests for cronclear.notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.notifier import NotifierConfig, _build_body, _build_subject, send_report
from cronclear.schedule_analyzer import AnalysisReport, ScheduleSummary


def _make_entry(command="backup.sh", user="root", host="web1", schedule="0 2 * * *"):
    return CronEntry(schedule=schedule, command=command, user=user, host=host)


def _make_summary(command="backup.sh", user="root", host="web1", freq=1.0):
    return ScheduleSummary(
        host=host,
        user=user,
        command=command,
        schedule="0 2 * * *",
        next_run=None,
        frequency_per_day=freq,
    )


def _empty_report():
    return AnalysisReport(total_jobs=0, summaries=[], duplicates={}, frequent_jobs=[])


def _rich_report():
    entry = _make_entry()
    return AnalysisReport(
        total_jobs=3,
        summaries=[_make_summary()],
        duplicates={"0 2 * * * backup.sh": [entry, _make_entry(host="web2")]},
        frequent_jobs=[_make_summary(freq=48.0)],
    )


# --- subject tests ---

def test_subject_all_clear():
    subject = _build_subject(_empty_report())
    assert "all clear" in subject


def test_subject_shows_duplicate_count():
    subject = _build_subject(_rich_report())
    assert "duplicate" in subject


def test_subject_shows_frequent_count():
    subject = _build_subject(_rich_report())
    assert "high-frequency" in subject


# --- body tests ---

def test_body_contains_total_jobs():
    body = _build_body(_rich_report())
    assert "Total jobs audited: 3" in body


def test_body_contains_duplicate_section():
    body = _build_body(_rich_report())
    assert "Duplicate Jobs" in body


def test_body_contains_frequent_section():
    body = _build_body(_rich_report())
    assert "High-Frequency" in body


def test_body_no_sections_when_empty():
    body = _build_body(_empty_report())
    assert "Duplicate" not in body
    assert "High-Frequency" not in body


# --- send_report tests ---

def test_send_report_returns_false_no_recipients():
    cfg = NotifierConfig(smtp_host="localhost", recipients=[])
    assert send_report(_empty_report(), cfg) is False


def test_send_report_calls_smtp(monkeypatch):
    mock_server = MagicMock()
    mock_server.__enter__ = lambda s: s
    mock_server.__exit__ = MagicMock(return_value=False)
    mock_factory = MagicMock(return_value=mock_server)

    cfg = NotifierConfig(
        smtp_host="smtp.example.com",
        recipients=["ops@example.com"],
        use_tls=False,
    )
    result = send_report(_empty_report(), cfg, smtp_factory=mock_factory)
    assert result is True
    mock_factory.assert_called_once_with("smtp.example.com", 587)
    mock_server.sendmail.assert_called_once()


def test_send_report_returns_false_on_smtp_error():
    def bad_factory(*_):
        raise OSError("connection refused")

    cfg = NotifierConfig(smtp_host="bad-host", recipients=["a@b.com"])
    assert send_report(_empty_report(), cfg, smtp_factory=bad_factory) is False
