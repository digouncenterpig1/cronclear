"""Group cron entries by schedule pattern or command prefix."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


@dataclass
class ScheduleGroup:
    """A set of entries sharing the same schedule expression."""

    schedule: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def host_count(self) -> int:
        hosts = {e.host for e in self.entries if e.host}
        return len(hosts)

    @property
    def command_count(self) -> int:
        return len(self.entries)


def group_by_schedule(results: List[CollectionResult]) -> Dict[str, ScheduleGroup]:
    """Return entries grouped by their schedule string."""
    groups: Dict[str, ScheduleGroup] = {}
    for result in results:
        for entry in result.entries:
            key = entry.schedule
            if key not in groups:
                groups[key] = ScheduleGroup(schedule=key)
            groups[key].entries.append(entry)
    return groups


def group_by_command_prefix(results: List[CollectionResult], depth: int = 1) -> Dict[str, List[CronEntry]]:
    """Group entries by the first *depth* path components of the command."""
    groups: Dict[str, List[CronEntry]] = defaultdict(list)
    for result in results:
        for entry in result.entries:
            parts = entry.command.strip().lstrip("/").split("/")
            prefix = "/" + "/".join(parts[:depth]) if parts else entry.command
            groups[prefix].append(entry)
    return dict(groups)


def unique_schedules(results: List[CollectionResult]) -> List[str]:
    """Return a sorted list of distinct schedule expressions."""
    seen = set()
    for result in results:
        for entry in result.entries:
            seen.add(entry.schedule)
    return sorted(seen)
