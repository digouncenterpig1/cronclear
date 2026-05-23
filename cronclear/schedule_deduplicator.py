"""Deduplicate cron entries across hosts, identifying redundant schedules."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


def _entry_fingerprint(entry: CronEntry) -> str:
    """Return a string key based on schedule + command, ignoring host/user."""
    return f"{entry.schedule}|{entry.command.strip()}"


@dataclass
class DeduplicatedGroup:
    """A group of entries that share the same schedule+command fingerprint."""

    fingerprint: str
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def hosts(self) -> List[str]:
        return [e.host for e in self.entries if e.host]

    @property
    def is_duplicate(self) -> bool:
        return len(self.entries) > 1

    @property
    def command(self) -> str:
        return self.entries[0].command if self.entries else ""

    @property
    def schedule(self) -> str:
        return self.entries[0].schedule if self.entries else ""


@dataclass
class DeduplicationReport:
    """Result of running deduplication across collected cron results."""

    groups: List[DeduplicatedGroup] = field(default_factory=list)

    @property
    def duplicate_groups(self) -> List[DeduplicatedGroup]:
        return [g for g in self.groups if g.is_duplicate]

    @property
    def unique_groups(self) -> List[DeduplicatedGroup]:
        return [g for g in self.groups if not g.is_duplicate]

    @property
    def total_entries(self) -> int:
        return sum(len(g.entries) for g in self.groups)

    @property
    def redundant_entry_count(self) -> int:
        """Number of entries that are duplicates (all but one per group)."""
        return sum(len(g.entries) - 1 for g in self.duplicate_groups)


def deduplicate_entries(
    results: List[CollectionResult],
) -> DeduplicationReport:
    """Group entries by fingerprint across all collection results."""
    index: Dict[str, DeduplicatedGroup] = {}

    for result in results:
        for parse_result in result.parse_results:
            for entry in parse_result.entries:
                fp = _entry_fingerprint(entry)
                if fp not in index:
                    index[fp] = DeduplicatedGroup(fingerprint=fp)
                index[fp].entries.append(entry)

    return DeduplicationReport(groups=list(index.values()))
