"""Summarize cron schedules across hosts into a human-readable digest."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


@dataclass
class HostSummary:
    host: str
    total_jobs: int
    unique_schedules: int
    most_common_schedule: str | None
    commands: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "total_jobs": self.total_jobs,
            "unique_schedules": self.unique_schedules,
            "most_common_schedule": self.most_common_schedule,
            "commands": self.commands,
        }


@dataclass
class DigestReport:
    host_summaries: List[HostSummary] = field(default_factory=list)
    total_hosts: int = 0
    total_jobs: int = 0
    global_unique_schedules: int = 0

    @property
    def average_jobs_per_host(self) -> float:
        if self.total_hosts == 0:
            return 0.0
        return self.total_jobs / self.total_hosts


def _most_common(schedules: List[str]) -> str | None:
    if not schedules:
        return None
    return max(set(schedules), key=schedules.count)


def summarize_results(results: List[CollectionResult]) -> DigestReport:
    """Build a DigestReport from a list of CollectionResults."""
    host_summaries: List[HostSummary] = []
    all_schedules: List[str] = []

    for result in results:
        if result.error or not result.entries:
            continue

        schedules = [e.schedule for e in result.entries]
        commands = [str(e) for e in result.entries]
        all_schedules.extend(schedules)

        summary = HostSummary(
            host=result.host,
            total_jobs=len(result.entries),
            unique_schedules=len(set(schedules)),
            most_common_schedule=_most_common(schedules),
            commands=commands,
        )
        host_summaries.append(summary)

    return DigestReport(
        host_summaries=host_summaries,
        total_hosts=len(host_summaries),
        total_jobs=sum(s.total_jobs for s in host_summaries),
        global_unique_schedules=len(set(all_schedules)),
    )
