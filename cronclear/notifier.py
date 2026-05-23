"""Simple notification helpers for alerting on high-frequency or duplicate cron jobs."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import List, Optional

from cronclear.schedule_analyzer import AnalysisReport


@dataclass
class NotifierConfig:
    smtp_host: str
    smtp_port: int = 587
    sender: str = "cronclear@localhost"
    recipients: List[str] = field(default_factory=list)
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True


def _build_subject(report: AnalysisReport) -> str:
    dup_count = sum(len(v) for v in report.duplicates.values())
    freq_count = len(report.frequent_jobs)
    parts = []
    if dup_count:
        parts.append(f"{dup_count} duplicate(s)")
    if freq_count:
        parts.append(f"{freq_count} high-frequency job(s)")
    suffix = ", ".join(parts) if parts else "all clear"
    return f"[cronclear] Cron audit: {suffix}"


def _build_body(report: AnalysisReport) -> str:
    lines: List[str] = [f"Total jobs audited: {report.total_jobs}", ""]

    if report.duplicates:
        lines.append("=== Duplicate Jobs ===")
        for schedule, entries in report.duplicates.items():
            lines.append(f"  {schedule}:")
            for e in entries:
                lines.append(f"    - {e.user}@{e.host}: {e.command}")
        lines.append("")

    if report.frequent_jobs:
        lines.append("=== High-Frequency Jobs (>= 24 runs/day) ===")
        for summary in report.frequent_jobs:
            lines.append(
                f"  [{summary.host}] {summary.user}: {summary.command} "
                f"({summary.frequency_per_day:.1f}/day)"
            )
        lines.append("")

    return "\n".join(lines)


def send_report(
    report: AnalysisReport,
    config: NotifierConfig,
    smtp_factory=None,
) -> bool:
    """Send an email notification for the given report.

    Returns True if the email was sent successfully, False otherwise.
    """
    if not config.recipients:
        return False

    subject = _build_subject(report)
    body = _build_body(report)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.sender
    msg["To"] = ", ".join(config.recipients)

    factory = smtp_factory or smtplib.SMTP
    try:
        with factory(config.smtp_host, config.smtp_port) as server:
            if config.use_tls:
                server.starttls()
            if config.username and config.password:
                server.login(config.username, config.password)
            server.sendmail(config.sender, config.recipients, msg.as_string())
    except Exception:
        return False
    return True
