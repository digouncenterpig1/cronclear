"""Full-text and field-based search across collected cron entries."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cronclear.cron_collector import CollectionResult
from cronclear.cron_parser import CronEntry


@dataclass
class SearchResult:
    entry: CronEntry
    host: str
    matched_field: str  # 'command', 'schedule', 'user', or 'any'


@dataclass
class SearchReport:
    query: str
    results: List[SearchResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def hosts(self) -> List[str]:
        return sorted({r.host for r in self.results})


def _entry_matches_text(entry: CronEntry, pattern: re.Pattern) -> Optional[str]:
    """Return which field first matched, or None."""
    if pattern.search(entry.command):
        return "command"
    if pattern.search(str(entry.schedule)):
        return "schedule"
    if entry.user and pattern.search(entry.user):
        return "user"
    return None


def search_entries(
    results: List[CollectionResult],
    query: str,
    *,
    field: Optional[str] = None,
    case_sensitive: bool = False,
) -> SearchReport:
    """Search cron entries across all collection results.

    Args:
        results: list of CollectionResult from CronCollector.
        query: regex or plain-text pattern to search for.
        field: restrict search to 'command', 'schedule', or 'user'.
        case_sensitive: whether the match is case-sensitive.
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query, flags)
    except re.error as exc:
        raise ValueError(f"Invalid search pattern: {exc}") from exc

    report = SearchReport(query=query)

    for cr in results:
        for entry in cr.parse_result.entries:
            if field == "command":
                matched = "command" if pattern.search(entry.command) else None
            elif field == "schedule":
                matched = "schedule" if pattern.search(str(entry.schedule)) else None
            elif field == "user":
                matched = "user" if (entry.user and pattern.search(entry.user)) else None
            else:
                matched = _entry_matches_text(entry, pattern)

            if matched:
                report.results.append(
                    SearchResult(entry=entry, host=cr.host, matched_field=matched)
                )

    return report
