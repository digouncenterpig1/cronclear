"""Watch for crontab changes across hosts by comparing snapshots."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from cronclear.cron_parser import CronEntry
from cronclear.schedule_differ import DiffResult, diff_entries


@dataclass
class Snapshot:
    host: str
    captured_at: datetime
    entries: List[CronEntry]

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "captured_at": self.captured_at.isoformat(),
            "entries": [
                {
                    "user": e.user,
                    "schedule": e.schedule,
                    "command": e.command,
                }
                for e in self.entries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        from cronclear.cron_parser import CronEntry  # local to avoid circular

        entries = [
            CronEntry(
                user=item["user"],
                host=data["host"],
                schedule=item["schedule"],
                command=item["command"],
            )
            for item in data.get("entries", [])
        ]
        return cls(
            host=data["host"],
            captured_at=datetime.fromisoformat(data["captured_at"]),
            entries=entries,
        )


@dataclass
class WatchReport:
    checked_at: datetime
    diffs: Dict[str, DiffResult] = field(default_factory=dict)

    @property
    def has_any_changes(self) -> bool:
        return any(d.has_changes for d in self.diffs.values())

    def summary_lines(self) -> List[str]:
        lines = []
        for host, diff in self.diffs.items():
            lines.append(f"{host}: {diff.summary_line()}")
        return lines


class ScheduleWatcher:
    """Persist snapshots to disk and produce diffs on subsequent runs."""

    def __init__(self, snapshot_dir: str) -> None:
        self.snapshot_dir = snapshot_dir
        os.makedirs(snapshot_dir, exist_ok=True)

    def _path(self, host: str) -> str:
        safe = host.replace("/", "_").replace(":", "_")
        return os.path.join(self.snapshot_dir, f"{safe}.json")

    def load_snapshot(self, host: str) -> Optional[Snapshot]:
        path = self._path(host)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as fh:
            return Snapshot.from_dict(json.load(fh))

    def save_snapshot(self, snapshot: Snapshot) -> None:
        path = self._path(snapshot.host)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snapshot.to_dict(), fh, indent=2)

    def watch(self, host: str, current_entries: List[CronEntry]) -> DiffResult:
        previous = self.load_snapshot(host)
        old_entries = previous.entries if previous else []
        result = diff_entries(old_entries, current_entries)
        new_snapshot = Snapshot(
            host=host,
            captured_at=datetime.now(timezone.utc),
            entries=current_entries,
        )
        self.save_snapshot(new_snapshot)
        return result

    def watch_many(self, host_entries: Dict[str, List[CronEntry]]) -> WatchReport:
        report = WatchReport(checked_at=datetime.now(timezone.utc))
        for host, entries in host_entries.items():
            report.diffs[host] = self.watch(host, entries)
        return report
