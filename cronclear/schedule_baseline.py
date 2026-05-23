"""Baseline management: capture and compare cron schedules against a known-good state."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cronclear.cron_parser import CronEntry


@dataclass
class BaselineEntry:
    raw: str
    user: str
    host: str

    def to_dict(self) -> dict:
        return {"raw": self.raw, "user": self.user, "host": self.host}

    @classmethod
    def from_dict(cls, data: dict) -> "BaselineEntry":
        return cls(raw=data["raw"], user=data["user"], host=data["host"])


@dataclass
class BaselineReport:
    added: List[BaselineEntry] = field(default_factory=list)
    removed: List[BaselineEntry] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)

    def summary_line(self) -> str:
        if not self.has_changes:
            return "No changes from baseline."
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.removed:
            parts.append(f"-{len(self.removed)} removed")
        return "Baseline diff: " + ", ".join(parts)


def _entry_key(e: BaselineEntry) -> str:
    return f"{e.host}|{e.user}|{e.raw}"


def save_baseline(entries: List[CronEntry], path: Path) -> None:
    """Persist a list of CronEntry objects as the new baseline."""
    data = [
        BaselineEntry(raw=e.raw, user=e.user or "", host=e.host or "").to_dict()
        for e in entries
    ]
    path.write_text(json.dumps(data, indent=2))


def load_baseline(path: Path) -> Optional[List[BaselineEntry]]:
    """Load a previously saved baseline. Returns None if file does not exist."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return [BaselineEntry.from_dict(d) for d in data]


def compare_to_baseline(
    current: List[CronEntry], baseline: List[BaselineEntry]
) -> BaselineReport:
    """Compare current entries against the baseline and return a diff report."""
    baseline_keys = {_entry_key(e): e for e in baseline}
    current_entries = [
        BaselineEntry(raw=e.raw, user=e.user or "", host=e.host or "")
        for e in current
    ]
    current_keys = {_entry_key(e): e for e in current_entries}

    added = [e for k, e in current_keys.items() if k not in baseline_keys]
    removed = [e for k, e in baseline_keys.items() if k not in current_keys]
    return BaselineReport(added=added, removed=removed)
