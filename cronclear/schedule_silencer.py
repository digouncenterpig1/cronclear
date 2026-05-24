"""Silence (suppress) cron entries matching user-defined rules so they
are excluded from reports and alerts."""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronclear.cron_parser import CronEntry


@dataclass
class SilenceRule:
    """A single suppression rule."""
    host_pattern: str = "*"          # glob, e.g. "web-*" or "*"
    command_pattern: str = "*"       # glob, e.g. "*/backup.sh*"
    reason: str = ""

    def matches(self, entry: CronEntry) -> bool:
        host_ok = fnmatch.fnmatch(entry.host or "", self.host_pattern)
        cmd_ok = fnmatch.fnmatch(entry.command, self.command_pattern)
        return host_ok and cmd_ok

    def to_dict(self) -> dict:
        return {
            "host_pattern": self.host_pattern,
            "command_pattern": self.command_pattern,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SilenceRule":
        return cls(
            host_pattern=d.get("host_pattern", "*"),
            command_pattern=d.get("command_pattern", "*"),
            reason=d.get("reason", ""),
        )


@dataclass
class SilenceReport:
    kept: List[CronEntry] = field(default_factory=list)
    silenced: List[CronEntry] = field(default_factory=list)

    @property
    def total_silenced(self) -> int:
        return len(self.silenced)


def load_rules(path: Path) -> List[SilenceRule]:
    """Load silence rules from a JSON file.  Returns [] if file missing."""
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [SilenceRule.from_dict(r) for r in data.get("rules", [])]


def save_rules(rules: List[SilenceRule], path: Path) -> None:
    path.write_text(json.dumps({"rules": [r.to_dict() for r in rules]}, indent=2))


def apply_silence(entries: List[CronEntry], rules: List[SilenceRule]) -> SilenceReport:
    """Partition *entries* into kept vs silenced based on *rules*."""
    report = SilenceReport()
    for entry in entries:
        if any(r.matches(entry) for r in rules):
            report.silenced.append(entry)
        else:
            report.kept.append(entry)
    return report


def matching_rule(entry: CronEntry, rules: List[SilenceRule]) -> Optional[SilenceRule]:
    """Return the first rule that matches *entry*, or None."""
    for rule in rules:
        if rule.matches(entry):
            return rule
    return None
