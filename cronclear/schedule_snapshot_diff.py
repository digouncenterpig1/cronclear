"""Compare two snapshots to produce a human-readable change report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronclear.schedule_watcher import Snapshot
from cronclear.schedule_differ import diff_entries, DiffResult


@dataclass
class HostDiff:
    host: str
    diff: DiffResult

    @property
    def has_changes(self) -> bool:
        return self.diff.has_changes


@dataclass
class SnapshotDiffReport:
    host_diffs: List[HostDiff] = field(default_factory=list)
    hosts_added: List[str] = field(default_factory=list)
    hosts_removed: List[str] = field(default_factory=list)

    @property
    def has_any_changes(self) -> bool:
        return (
            bool(self.hosts_added)
            or bool(self.hosts_removed)
            or any(hd.has_changes for hd in self.host_diffs)
        )

    @property
    def total_added(self) -> int:
        return sum(len(hd.diff.added) for hd in self.host_diffs)

    @property
    def total_removed(self) -> int:
        return sum(len(hd.diff.removed) for hd in self.host_diffs)

    def summary_lines(self) -> List[str]:
        lines: List[str] = []
        for host in self.hosts_added:
            lines.append(f"[+host] {host}")
        for host in self.hosts_removed:
            lines.append(f"[-host] {host}")
        for hd in self.host_diffs:
            if hd.has_changes:
                lines.append(f"[~] {hd.host}: {hd.diff.summary_line()}")
        return lines


def diff_snapshots(
    old: Optional[Snapshot], new: Snapshot
) -> SnapshotDiffReport:
    """Diff two snapshots; if *old* is None treat everything as added."""
    report = SnapshotDiffReport()

    old_hosts: Dict[str, Snapshot] = {}
    if old is not None:
        # Build per-host entry lookup from old snapshot
        old_hosts = {old.host: old} if old.host else {}

    new_host = new.host

    if old is None:
        # Everything is new
        result = diff_entries([], new.entries)
        report.host_diffs.append(HostDiff(host=new_host, diff=result))
        return report

    old_snap = old_hosts.get(new_host)
    old_entries = old_snap.entries if old_snap else []
    result = diff_entries(old_entries, new.entries)
    report.host_diffs.append(HostDiff(host=new_host, diff=result))
    return report
