"""Compare cron schedules across two sets of hosts and report differences."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


@dataclass
class HostComparison:
    host_a: str
    host_b: str
    only_in_a: List[CronEntry] = field(default_factory=list)
    only_in_b: List[CronEntry] = field(default_factory=list)
    shared: List[Tuple[CronEntry, CronEntry]] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.only_in_a or self.only_in_b)

    @property
    def difference_count(self) -> int:
        return len(self.only_in_a) + len(self.only_in_b)


@dataclass
class ComparisonReport:
    comparisons: List[HostComparison] = field(default_factory=list)

    @property
    def total_pairs(self) -> int:
        return len(self.comparisons)

    @property
    def differing_pairs(self) -> List[HostComparison]:
        return [c for c in self.comparisons if c.has_differences]


def _entry_key(entry: CronEntry) -> str:
    return f"{entry.schedule}|{entry.command.strip()}"


def compare_hosts(
    result_a: CollectionResult,
    result_b: CollectionResult,
) -> HostComparison:
    keys_a = {_entry_key(e): e for e in result_a.entries}
    keys_b = {_entry_key(e): e for e in result_b.entries}

    only_a = [e for k, e in keys_a.items() if k not in keys_b]
    only_b = [e for k, e in keys_b.items() if k not in keys_a]
    shared = [(keys_a[k], keys_b[k]) for k in keys_a if k in keys_b]

    return HostComparison(
        host_a=result_a.host,
        host_b=result_b.host,
        only_in_a=only_a,
        only_in_b=only_b,
        shared=shared,
    )


def compare_all(
    results: List[CollectionResult],
    pairs: List[Tuple[str, str]],
) -> ComparisonReport:
    by_host: Dict[str, CollectionResult] = {r.host: r for r in results}
    comparisons = []
    for host_a, host_b in pairs:
        if host_a in by_host and host_b in by_host:
            comparisons.append(compare_hosts(by_host[host_a], by_host[host_b]))
    return ComparisonReport(comparisons=comparisons)
