"""Diff cron schedules between two snapshots or host groups."""

from dataclasses import dataclass, field
from typing import List, Tuple

from cronclear.cron_parser import CronEntry


@dataclass
class DiffResult:
    """Result of comparing two sets of cron entries."""

    added: List[CronEntry] = field(default_factory=list)
    removed: List[CronEntry] = field(default_factory=list)
    unchanged: List[CronEntry] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)

    @property
    def summary_line(self) -> str:
        return (
            f"+{len(self.added)} added, "
            f"-{len(self.removed)} removed, "
            f"{len(self.unchanged)} unchanged"
        )


def _entry_key(entry: CronEntry) -> Tuple[str, str, str]:
    """Stable identity key for a cron entry (host, user, command)."""
    return (entry.host or "", entry.user or "", entry.command)


def diff_entries(
    before: List[CronEntry],
    after: List[CronEntry],
) -> DiffResult:
    """Compare two lists of CronEntry objects and return a DiffResult.

    Entries are matched by (host, user, command). Schedule changes on an
    otherwise identical key are reported as a removal + addition pair.
    """
    before_map = {_entry_key(e): e for e in before}
    after_map = {_entry_key(e): e for e in after}

    added: List[CronEntry] = []
    removed: List[CronEntry] = []
    unchanged: List[CronEntry] = []

    for key, entry in after_map.items():
        if key not in before_map:
            added.append(entry)
        elif before_map[key].schedule != entry.schedule:
            # same identity but schedule changed — treat as remove + add
            removed.append(before_map[key])
            added.append(entry)
        else:
            unchanged.append(entry)

    for key, entry in before_map.items():
        if key not in after_map:
            removed.append(entry)

    return DiffResult(added=added, removed=removed, unchanged=unchanged)
