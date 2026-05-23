"""Export analysis reports to JSON or CSV formats."""

from __future__ import annotations

import csv
import json
import io
from typing import Union

from cronclear.schedule_analyzer import AnalysisReport


def export_json(report: AnalysisReport, indent: int = 2) -> str:
    """Serialize an AnalysisReport to a JSON string."""
    data: dict = {
        "total_jobs": report.total_jobs,
        "summaries": [
            {
                "host": s.host,
                "user": s.user,
                "schedule": s.schedule,
                "command": s.command,
                "frequency_per_day": s.frequency_per_day,
                "next_run": s.next_run.isoformat() if s.next_run else None,
            }
            for s in report.summaries
        ],
        "duplicates": [
            [
                {"host": e.host, "user": e.user, "schedule": e.schedule, "command": e.command}
                for e in group
            ]
            for group in report.duplicates
        ],
        "frequent_jobs": [
            {"host": s.host, "user": s.user, "schedule": s.schedule, "command": s.command,
             "frequency_per_day": s.frequency_per_day}
            for s in report.frequent_jobs
        ],
    }
    return json.dumps(data, indent=indent)


def export_csv(report: AnalysisReport) -> str:
    """Serialize an AnalysisReport summaries to a CSV string."""
    output = io.StringIO()
    fieldnames = ["host", "user", "schedule", "command", "frequency_per_day", "next_run"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for s in report.summaries:
        writer.writerow({
            "host": s.host,
            "user": s.user,
            "schedule": s.schedule,
            "command": s.command,
            "frequency_per_day": s.frequency_per_day,
            "next_run": s.next_run.isoformat() if s.next_run else "",
        })
    return output.getvalue()


def export_report(report: AnalysisReport, fmt: str) -> str:
    """Export report in the given format ('json' or 'csv')."""
    fmt = fmt.lower()
    if fmt == "json":
        return export_json(report)
    if fmt == "csv":
        return export_csv(report)
    raise ValueError(f"Unsupported export format: {fmt!r}. Choose 'json' or 'csv'.")
