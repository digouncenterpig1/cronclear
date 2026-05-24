"""Lint cron entries for common mistakes and suspicious patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


@dataclass
class LintIssue:
    host: str
    user: str
    command: str
    schedule: str
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.host} ({self.user}): `{self.schedule}` — {self.message}"


@dataclass
class LintReport:
    issues: List[LintIssue] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.issues)

    def by_code(self, code: str) -> List[LintIssue]:
        return [i for i in self.issues if i.code == code]

    def has_issues(self) -> bool:
        return bool(self.issues)


_RISKY_COMMANDS = ("rm ", "dd ", "mkfs", "> /dev/", "chmod 777")
_NOISY_SCHEDULES = ("* * * * *", "*/1 * * * *")


def _lint_entry(entry: CronEntry) -> List[LintIssue]:
    issues: List[LintIssue] = []
    sched = str(entry.schedule)
    cmd = entry.command.strip()
    host = entry.host or ""
    user = entry.user or ""

    if sched in _NOISY_SCHEDULES:
        issues.append(LintIssue(
            host=host, user=user, command=cmd, schedule=sched,
            code="NOISY",
            message="Job runs every minute — consider a less frequent schedule",
        ))

    if not cmd:
        issues.append(LintIssue(
            host=host, user=user, command=cmd, schedule=sched,
            code="EMPTY_CMD",
            message="Cron entry has an empty command",
        ))

    for pattern in _RISKY_COMMANDS:
        if pattern in cmd:
            issues.append(LintIssue(
                host=host, user=user, command=cmd, schedule=sched,
                code="RISKY_CMD",
                message=f"Command contains potentially destructive pattern: '{pattern.strip()}'",
            ))
            break

    if not entry.is_shortcut and sched.count(" ") < 4:
        issues.append(LintIssue(
            host=host, user=user, command=cmd, schedule=sched,
            code="MALFORMED",
            message="Schedule does not have 5 fields and is not a recognised shortcut",
        ))

    return issues


def lint_results(results: List[CollectionResult]) -> LintReport:
    report = LintReport()
    for result in results:
        for entry in result.entries:
            report.issues.extend(_lint_entry(entry))
    return report
