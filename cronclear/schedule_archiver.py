"""Archive cron collection results to a timestamped JSON file for historical review."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronclear.cron_collector import CollectionResult
from cronclear.cron_parser import CronEntry


@dataclass
class ArchiveEntry:
    timestamp: str
    host: str
    user: str
    schedule: str
    command: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "host": self.host,
            "user": self.user,
            "schedule": self.schedule,
            "command": self.command,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ArchiveEntry":
        return cls(
            timestamp=d["timestamp"],
            host=d["host"],
            user=d["user"],
            schedule=d["schedule"],
            command=d["command"],
        )


@dataclass
class ArchiveReport:
    path: Path
    entry_count: int
    hosts: List[str] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def archive_results(
    results: List[CollectionResult],
    archive_dir: Path,
    timestamp: Optional[str] = None,
) -> ArchiveReport:
    """Serialize all cron entries from results into a timestamped JSON archive file."""
    archive_dir = Path(archive_dir)
    archive_dir.mkdir(parents=True, exist_ok=True)

    ts = timestamp or _now_iso()
    safe_ts = ts.replace(":", "-").replace("+", "Z")
    out_path = archive_dir / f"cron_archive_{safe_ts}.json"

    entries: List[dict] = []
    hosts_seen: List[str] = []

    for result in results:
        if result.host not in hosts_seen:
            hosts_seen.append(result.host)
        for entry in result.entries:
            ae = ArchiveEntry(
                timestamp=ts,
                host=result.host,
                user=getattr(entry, "user", "unknown"),
                schedule=entry.schedule,
                command=str(entry),
            )
            entries.append(ae.to_dict())

    out_path.write_text(json.dumps({"archived_at": ts, "entries": entries}, indent=2))
    return ArchiveReport(path=out_path, entry_count=len(entries), hosts=hosts_seen)


def load_archive(path: Path) -> List[ArchiveEntry]:
    """Load archive entries from a previously saved archive file."""
    data = json.loads(Path(path).read_text())
    return [ArchiveEntry.from_dict(e) for e in data.get("entries", [])]
