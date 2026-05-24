"""Merge cron entries from multiple hosts into a unified deduplicated view.

Useful when you want a single canonical list of what runs across your fleet,
collapsing identical jobs that appear on many hosts into one record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


def _job_key(entry: CronEntry) -> Tuple[str, str]:
    """Return a (schedule, command) key that identifies a unique job."""
    schedule = entry.schedule.strip()
    command = " ".join(entry.command.split())  # normalise whitespace
    return (schedule, command)


@dataclass
class MergedJob:
    """A single logical job that may exist on one or more hosts."""

    schedule: str
    command: str
    hosts: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)

    @property
    def host_count(self) -> int:
        return len(self.hosts)

    @property
    def is_shared(self) -> bool:
        """True when the same job runs on more than one host."""
        return self.host_count > 1

    def to_dict(self) -> Dict:
        return {
            "schedule": self.schedule,
            "command": self.command,
            "hosts": self.hosts,
            "users": self.users,
            "host_count": self.host_count,
            "is_shared": self.is_shared,
        }


@dataclass
class MergeReport:
    """Result of merging cron entries across a collection of hosts."""

    jobs: List[MergedJob] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of distinct logical jobs."""
        return len(self.jobs)

    @property
    def shared_jobs(self) -> List[MergedJob]:
        """Jobs that appear on more than one host."""
        return [j for j in self.jobs if j.is_shared]

    @property
    def unique_jobs(self) -> List[MergedJob]:
        """Jobs that appear on exactly one host."""
        return [j for j in self.jobs if not j.is_shared]

    @property
    def host_count(self) -> int:
        """Number of distinct hosts represented in this report."""
        hosts: set = set()
        for job in self.jobs:
            hosts.update(job.hosts)
        return len(hosts)


def merge_results(results: List[CollectionResult]) -> MergeReport:
    """Merge cron entries from multiple *CollectionResult* objects.

    Entries that share the same normalised schedule and command are collapsed
    into a single *MergedJob*; the hosts and users lists record every
    occurrence.

    Args:
        results: Collection results gathered by *CronCollector*.

    Returns:
        A *MergeReport* containing one *MergedJob* per distinct (schedule,
        command) pair.
    """
    merged: Dict[Tuple[str, str], MergedJob] = {}

    for result in results:
        if result.error:
            continue
        for entry in result.entries:
            key = _job_key(entry)
            if key not in merged:
                merged[key] = MergedJob(
                    schedule=key[0],
                    command=key[1],
                )
            job = merged[key]
            host = entry.host or "unknown"
            if host not in job.hosts:
                job.hosts.append(host)
            user = entry.user or ""
            if user and user not in job.users:
                job.users.append(user)

    # Sort for deterministic output: shared jobs first, then alphabetically
    jobs = sorted(
        merged.values(),
        key=lambda j: (-j.host_count, j.schedule, j.command),
    )
    return MergeReport(jobs=jobs)
