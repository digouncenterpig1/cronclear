"""Tests for cronclear.exporter."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from cronclear.exporter import export_csv, export_json, export_report
from cronclear.schedule_analyzer import AnalysisReport, ScheduleSummary


def _make_summary(host="web1", user="root", schedule="*/5 * * * *",
                  command="/usr/bin/check", freq=288.0, next_run=None) -> ScheduleSummary:
    s = MagicMock(spec=ScheduleSummary)
    s.host = host
    s.user = user
    s.schedule = schedule
    s.command = command
    s.frequency_per_day = freq
    s.next_run = next_run
    return s


def _make_report(summaries=None, duplicates=None, frequent_jobs=None) -> AnalysisReport:
    r = MagicMock(spec=AnalysisReport)
    r.summaries = summaries or []
    r.duplicates = duplicates or []
    r.frequent_jobs = frequent_jobs or []
    r.total_jobs = len(r.summaries)
    return r


def test_export_json_structure():
    s = _make_summary(next_run=datetime(2024, 6, 1, 12, 0, 0))
    report = _make_report(summaries=[s])
    result = export_json(report)
    data = json.loads(result)
    assert data["total_jobs"] == 1
    assert len(data["summaries"]) == 1
    entry = data["summaries"][0]
    assert entry["host"] == "web1"
    assert entry["next_run"] == "2024-06-01T12:00:00"


def test_export_json_next_run_none():
    s = _make_summary(next_run=None)
    report = _make_report(summaries=[s])
    data = json.loads(export_json(report))
    assert data["summaries"][0]["next_run"] is None


def test_export_json_duplicates():
    s1 = _make_summary(host="web1")
    s2 = _make_summary(host="web2")
    report = _make_report(duplicates=[[s1, s2]])
    data = json.loads(export_json(report))
    assert len(data["duplicates"]) == 1
    assert data["duplicates"][0][0]["host"] == "web1"


def test_export_csv_headers():
    report = _make_report()
    result = export_csv(report)
    reader = csv.DictReader(io.StringIO(result))
    assert set(reader.fieldnames) == {"host", "user", "schedule", "command",
                                       "frequency_per_day", "next_run"}


def test_export_csv_row_values():
    s = _make_summary(next_run=datetime(2024, 1, 15, 8, 30))
    report = _make_report(summaries=[s])
    result = export_csv(report)
    rows = list(csv.DictReader(io.StringIO(result)))
    assert len(rows) == 1
    assert rows[0]["host"] == "web1"
    assert rows[0]["next_run"] == "2024-01-15T08:30:00"


def test_export_csv_next_run_empty_when_none():
    s = _make_summary(next_run=None)
    report = _make_report(summaries=[s])
    rows = list(csv.DictReader(io.StringIO(export_csv(report))))
    assert rows[0]["next_run"] == ""


def test_export_report_dispatches_json():
    report = _make_report()
    result = export_report(report, "json")
    json.loads(result)  # should not raise


def test_export_report_dispatches_csv():
    report = _make_report()
    result = export_report(report, "csv")
    assert "host" in result


def test_export_report_invalid_format_raises():
    report = _make_report()
    with pytest.raises(ValueError, match="Unsupported export format"):
        export_report(report, "xml")
