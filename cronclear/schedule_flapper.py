"""Detect 'flapping' cron entries — jobs that appear in some snapshots but not others."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from cronclear.schedule_watcher import Snapshot


@dataclass
class FlapEntry:
    host: str
    raw: str
    present_in: List[str]  # snapshot labels / paths where entry appeared
    absent_in: List[str]   # snapshot labels / paths where entry was missing

    @property
    def flap_ratio(self) -> float:
        """Fraction of snapshots where the entry was *absent*."""
        total = len(self.present_in) + len(self.absent_in)
        return len(self.absent_in) / total if total else 0.0

    @property
    def is_flapping(self) -> bool:
        return 0 < self.flap_ratio < 1.0


@dataclass
class FlapReport:
    entries: List[FlapEntry] = field(default_factory=list)

    @property
    def flapping(self) -> List[FlapEntry]:
        return [e for e in self.entries if e.is_flapping]

    @property
    def has_flappers(self) -> bool:
        return bool(self.flapping)


def _entry_key(host: str, raw: str) -> tuple:
    return (host, raw.strip())


def detect_flapping(
    snapshots: Sequence[Snapshot],
    labels: Sequence[str] | None = None,
) -> FlapReport:
    """Given an ordered list of snapshots, return a FlapReport.

    Args:
        snapshots: Ordered collection of Snapshot objects.
        labels:    Optional human-readable label per snapshot (defaults to
                   "snap-0", "snap-1", …).
    """
    if labels is None:
        labels = [f"snap-{i}" for i in range(len(snapshots))]

    if len(labels) != len(snapshots):
        raise ValueError("labels length must match snapshots length")

    # key -> {label: bool present}
    presence: Dict[tuple, Dict[str, bool]] = {}

    for snap, label in zip(snapshots, labels):
        seen: set = set()
        for host, entries in snap.entries.items():
            for entry in entries:
                k = _entry_key(host, str(entry))
                seen.add(k)
                presence.setdefault(k, {})[label] = True

        # mark absent for keys not seen in this snapshot
        for k in presence:
            if label not in presence[k]:
                presence[k][label] = False

    report = FlapReport()
    for (host, raw), label_map in presence.items():
        present_in = [lbl for lbl, v in label_map.items() if v]
        absent_in  = [lbl for lbl, v in label_map.items() if not v]
        report.entries.append(
            FlapEntry(host=host, raw=raw, present_in=present_in, absent_in=absent_in)
        )

    return report
