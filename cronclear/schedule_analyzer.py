"""Analyze and summarize cron schedules collected from remote hosts."""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Dict
from croniter import croniter
from datetime import datetime, timedelta

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


@dataclass
class ScheduleSummary:
    host: str
    user: str
    command: str
    schedule: str
    next_run: datetime | None
    frequency_per_day: float
    is_frequent: bool  # runs more than 24 times/day


@dataclass
class AnalysisReport:
    summaries: List[ScheduleSummary] = field(default_factory=list)
    duplicates: Dict[str, List[ScheduleSummary]] = field(default_factory=dict)
    frequent_jobs: List[ScheduleSummary] = field(default_factory=list)

    @property
    def total_jobs(self) -> int:
        return len(self.summaries)


def _next_run(schedule: str) -> datetime | None:
    try:
        it = croniter(schedule, datetime.now())
        return it.get_next(datetime)
    except Exception:
        return None


def _frequency_per_day(schedule: str) -> float:
    try:
        base = datetime.now()
        it = croniter(schedule, base)
        runs = [it.get_next(datetime) for _ in range(100)]
        if len(runs) < 2:
            return 0.0
        span = (runs[-1] - runs[0]).total_seconds()
        if span == 0:
            return 0.0
        return 99 / (span / 86400)
    except Exception:
        return 0.0


def analyze(results: List[CollectionResult]) -> AnalysisReport:
    report = AnalysisReport()
    command_index: Dict[str, List[ScheduleSummary]] = defaultdict(list)

    for result in results:
        for entry in result.entries:
            freq = _frequency_per_day(entry.schedule)
            summary = ScheduleSummary(
                host=entry.host or result.host,
                user=entry.user or "unknown",
                command=entry.command,
                schedule=entry.schedule,
                next_run=_next_run(entry.schedule),
                frequency_per_day=freq,
                is_frequent=freq > 24,
            )
            report.summaries.append(summary)
            command_index[entry.command].append(summary)
            if summary.is_frequent:
                report.frequent_jobs.append(summary)

    report.duplicates = {
        cmd: entries for cmd, entries in command_index.items() if len(entries) > 1
    }
    return report
