"""Attach human-readable labels to cron entries based on their schedule pattern."""
from dataclasses import dataclass, field
from typing import List, Optional
from cronclear.cron_parser import CronEntry


_LABELS = [
    (lambda e: e.schedule == "@reboot", "on reboot"),
    (lambda e: e.schedule in ("@hourly", "0 * * * *"), "hourly"),
    (lambda e: e.schedule in ("@daily", "@midnight", "0 0 * * *"), "daily"),
    (lambda e: e.schedule in ("@weekly", "0 0 * * 0"), "weekly"),
    (lambda e: e.schedule in ("@monthly", "0 0 1 * *"), "monthly"),
    (lambda e: e.schedule in ("@yearly", "@annually", "0 0 1 1 *"), "yearly"),
    (lambda e: _field(e, 0) == "*" and not e.is_shortcut, "every minute"),
    (lambda e: _field(e, 0).startswith("*/"), "every N minutes"),
    (lambda e: _field(e, 1).startswith("*/"), "every N hours"),
]


def _field(entry: CronEntry, idx: int) -> str:
    parts = entry.schedule.split()
    return parts[idx] if len(parts) > idx else ""


@dataclass
class AnnotatedEntry:
    entry: CronEntry
    label: str
    note: Optional[str] = None


@dataclass
class AnnotationReport:
    entries: List[AnnotatedEntry] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.entries)

    def by_label(self, label: str) -> List[AnnotatedEntry]:
        return [a for a in self.entries if a.label == label]


def _resolve_label(entry: CronEntry) -> str:
    for predicate, label in _LABELS:
        try:
            if predicate(entry):
                return label
        except Exception:
            pass
    return "custom"


def annotate_entries(entries: List[CronEntry], notes: Optional[dict] = None) -> AnnotationReport:
    """Annotate a list of CronEntry objects with schedule labels.

    Args:
        entries: list of CronEntry instances to annotate.
        notes: optional mapping of command substring -> note string.

    Returns:
        AnnotationReport containing all annotated entries.
    """
    notes = notes or {}
    result = []
    for entry in entries:
        label = _resolve_label(entry)
        note = next((v for k, v in notes.items() if k in entry.command), None)
        result.append(AnnotatedEntry(entry=entry, label=label, note=note))
    return AnnotationReport(entries=result)
