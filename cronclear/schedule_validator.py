"""Validates cron entries for correctness beyond basic parsing.

Checks field ranges, step values, and overall expression sanity
so downstream tools can trust the data they receive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronclear.cron_parser import CronEntry

# Valid ranges for each positional cron field
_FIELD_RANGES = {
    "minute":     (0, 59),
    "hour":       (0, 23),
    "day_of_month": (1, 31),
    "month":      (1, 12),
    "day_of_week": (0, 7),   # 7 is Sunday alias on many systems
}

# Shortcut expressions that are always considered valid
_VALID_SHORTCUTS = {
    "@reboot", "@yearly", "@annually", "@monthly",
    "@weekly", "@daily", "@midnight", "@hourly",
}


@dataclass
class ValidationIssue:
    """A single validation problem found in a cron entry."""

    code: str          # short machine-readable code, e.g. "RANGE_EXCEEDED"
    message: str       # human-readable description
    entry: CronEntry

    def __str__(self) -> str:
        host = self.entry.host or "unknown"
        return f"[{self.code}] {host}: {self.entry} — {self.message}"


@dataclass
class ValidationReport:
    """Aggregated results of validating a collection of cron entries."""

    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.issues)

    @property
    def is_valid(self) -> bool:
        return self.total == 0

    def by_code(self, code: str) -> List[ValidationIssue]:
        """Return all issues matching *code*."""
        return [i for i in self.issues if i.code == code]


def _parse_int(value: str) -> Optional[int]:
    """Return int or None if *value* is not a plain integer."""
    try:
        return int(value)
    except ValueError:
        return None


def _validate_field(
    raw: str,
    name: str,
    low: int,
    high: int,
    entry: CronEntry,
) -> List[ValidationIssue]:
    """Validate a single cron field token and return any issues found."""
    issues: List[ValidationIssue] = []

    # Handle step expressions like */5 or 1-5/2
    base, _, step_str = raw.partition("/")
    if step_str:
        step = _parse_int(step_str)
        if step is None or step < 1:
            issues.append(ValidationIssue(
                code="INVALID_STEP",
                message=f"Field '{name}' has invalid step value '{step_str}'",
                entry=entry,
            ))

    # Handle range expressions like 1-5
    if "-" in base:
        parts = base.split("-", 1)
        lo = _parse_int(parts[0])
        hi = _parse_int(parts[1]) if len(parts) > 1 else None
        for val, label in ((lo, "start"), (hi, "end")):
            if val is None:
                issues.append(ValidationIssue(
                    code="INVALID_RANGE",
                    message=f"Field '{name}' has non-numeric range {label}: '{base}'",
                    entry=entry,
                ))
            elif not (low <= val <= high):
                issues.append(ValidationIssue(
                    code="RANGE_EXCEEDED",
                    message=(
                        f"Field '{name}' value {val} is outside "
                        f"allowed range {low}-{high}"
                    ),
                    entry=entry,
                ))
        if lo is not None and hi is not None and lo > hi:
            issues.append(ValidationIssue(
                code="INVALID_RANGE",
                message=f"Field '{name}' range start {lo} > end {hi}",
                entry=entry,
            ))
        return issues

    # Plain wildcard — always valid
    if base == "*":
        return issues

    # Comma-separated list
    for token in base.split(","):
        val = _parse_int(token)
        if val is None:
            issues.append(ValidationIssue(
                code="INVALID_VALUE",
                message=f"Field '{name}' contains non-numeric token '{token}'",
                entry=entry,
            ))
        elif not (low <= val <= high):
            issues.append(ValidationIssue(
                code="RANGE_EXCEEDED",
                message=(
                    f"Field '{name}' value {val} is outside "
                    f"allowed range {low}-{high}"
                ),
                entry=entry,
            ))

    return issues


def validate_entry(entry: CronEntry) -> List[ValidationIssue]:
    """Return a list of :class:`ValidationIssue` objects for *entry*.

    An empty list means the entry is considered valid.
    """
    schedule = entry.schedule

    # Shortcut expressions need no further field-level checks
    if schedule.strip().startswith("@"):
        if schedule.strip() not in _VALID_SHORTCUTS:
            return [ValidationIssue(
                code="UNKNOWN_SHORTCUT",
                message=f"Unrecognised shortcut expression '{schedule}'",
                entry=entry,
            )]
        return []

    parts = schedule.split()
    if len(parts) != 5:
        return [ValidationIssue(
            code="WRONG_FIELD_COUNT",
            message=(
                f"Expected 5 cron fields, got {len(parts)} "
                f"in expression '{schedule}'"
            ),
            entry=entry,
        )]

    field_names = list(_FIELD_RANGES.keys())
    issues: List[ValidationIssue] = []
    for raw, name in zip(parts, field_names):
        lo, hi = _FIELD_RANGES[name]
        issues.extend(_validate_field(raw, name, lo, hi, entry))

    return issues


def validate_entries(entries: List[CronEntry]) -> ValidationReport:
    """Validate every entry in *entries* and return a :class:`ValidationReport`."""
    report = ValidationReport()
    for entry in entries:
        report.issues.extend(validate_entry(entry))
    return report
