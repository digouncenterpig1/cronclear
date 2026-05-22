"""Tests for reporter module."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from cronclear.reporter import render_summary_table, render_duplicates, render_frequent_jobs, render_report
from cronclear.schedule_analyzer import AnalysisReport, ScheduleSummary


def _make_summary(
    host="host1",
    user="root",
    command="/bin/job.sh",
    schedule="0 2 * * *",
    next_run=None,
    frequency_per_day=1.0,
    is_frequent=False,
) -> ScheduleSummary:
    return ScheduleSummary(
        host=host,
        user=user,
        command=command,
        schedule=schedule,
        next_run=next_run or datetime.now() + timedelta(hours=2),
        frequency_per_day=frequency_per_day,
        is_frequent=is_frequent,
    )


@patch("cronclear.reporter.console")
def test_render_summary_table_called(mock_console):
    report = AnalysisReport(summaries=[_make_summary()])
    render_summary_table(report)
    mock_console.print.assert_called_once()


@patch("cronclear.reporter.console")
def test_render_duplicates_no_dups(mock_console):
    report = AnalysisReport()
    render_duplicates(report)
    mock_console.print.assert_called_once()
    call_args = mock_console.print.call_args[0][0]
    assert "No duplicate" in call_args


@patch("cronclear.reporter.console")
def test_render_duplicates_with_dups(mock_console):
    s1 = _make_summary(host="h1")
    s2 = _make_summary(host="h2")
    report = AnalysisReport(
        summaries=[s1, s2],
        duplicates={"/bin/job.sh": [s1, s2]},
    )
    render_duplicates(report)
    assert mock_console.print.call_count >= 2


@patch("cronclear.reporter.console")
def test_render_frequent_jobs_empty(mock_console):
    report = AnalysisReport()
    render_frequent_jobs(report)
    mock_console.print.assert_not_called()


@patch("cronclear.reporter.console")
def test_render_frequent_jobs_present(mock_console):
    s = _make_summary(is_frequent=True, frequency_per_day=1440.0)
    report = AnalysisReport(summaries=[s], frequent_jobs=[s])
    render_frequent_jobs(report)
    mock_console.print.assert_called()


@patch("cronclear.reporter.render_frequent_jobs")
@patch("cronclear.reporter.render_duplicates")
@patch("cronclear.reporter.render_summary_table")
def test_render_report_calls_all(mock_table, mock_dups, mock_freq):
    report = AnalysisReport()
    render_report(report)
    mock_table.assert_called_once_with(report)
    mock_dups.assert_called_once_with(report)
    mock_freq.assert_called_once_with(report)
