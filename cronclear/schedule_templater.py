"""schedule_templater.py — Match cron entries against known schedule templates.

A template describes a named, well-known schedule pattern (e.g. "nightly backup",
"weekly report") so teams can quickly see which jobs follow recognised patterns
and which are one-offs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult


@dataclass
class ScheduleTemplate:
    """A named schedule pattern with an optional description."""

    name: str
    # Canonical cron expression to match against (5-field, no shortcuts)
    expression: str
    description: str = ""

    def matches(self, entry: CronEntry) -> bool:
        """Return True when *entry* has the same 5-field schedule expression."""
        if entry.is_shortcut:
            return False
        return entry.schedule == self.expression


# ---------------------------------------------------------------------------
# Built-in well-known templates
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATES: List[ScheduleTemplate] = [
    ScheduleTemplate("every_minute",   "* * * * *",       "Runs every minute"),
    ScheduleTemplate("every_5min",     "*/5 * * * *",     "Runs every 5 minutes"),
    ScheduleTemplate("every_15min",    "*/15 * * * *",    "Runs every 15 minutes"),
    ScheduleTemplate("every_30min",    "*/30 * * * *",    "Runs every 30 minutes"),
    ScheduleTemplate("hourly",         "0 * * * *",       "Runs at the top of every hour"),
    ScheduleTemplate("daily_midnight", "0 0 * * *",       "Runs daily at midnight"),
    ScheduleTemplate("daily_noon",     "0 12 * * *",      "Runs daily at noon"),
    ScheduleTemplate("weekly_sunday",  "0 0 * * 0",       "Runs weekly on Sunday at midnight"),
    ScheduleTemplate("weekly_monday",  "0 0 * * 1",       "Runs weekly on Monday at midnight"),
    ScheduleTemplate("monthly_first",  "0 0 1 * *",       "Runs on the 1st of every month"),
    ScheduleTemplate("yearly",         "0 0 1 1 *",       "Runs once a year on Jan 1st"),
]


@dataclass
class TemplateMatch:
    """A single entry that matched a known template."""

    entry: CronEntry
    template: ScheduleTemplate


@dataclass
class TemplateReport:
    """Aggregated results of matching entries against templates."""

    matches: List[TemplateMatch] = field(default_factory=list)
    unmatched: List[CronEntry] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.matches) + len(self.unmatched)

    @property
    def matched_count(self) -> int:
        return len(self.matches)

    def by_template(self, name: str) -> List[TemplateMatch]:
        """Return all matches for a given template name."""
        return [m for m in self.matches if m.template.name == name]

    def template_names_used(self) -> List[str]:
        """Return sorted list of template names that had at least one match."""
        seen = {m.template.name for m in self.matches}
        return sorted(seen)


def match_entries(
    entries: Sequence[CronEntry],
    templates: Optional[List[ScheduleTemplate]] = None,
) -> TemplateReport:
    """Match *entries* against *templates* (defaults to DEFAULT_TEMPLATES).

    Each entry is checked against every template in order; the first match wins.
    Entries that do not match any template are placed in ``unmatched``.
    """
    if templates is None:
        templates = DEFAULT_TEMPLATES

    report = TemplateReport()
    for entry in entries:
        matched: Optional[ScheduleTemplate] = None
        for tmpl in templates:
            if tmpl.matches(entry):
                matched = tmpl
                break
        if matched is not None:
            report.matches.append(TemplateMatch(entry=entry, template=matched))
        else:
            report.unmatched.append(entry)
    return report


def match_from_results(
    results: Sequence[CollectionResult],
    templates: Optional[List[ScheduleTemplate]] = None,
) -> TemplateReport:
    """Convenience wrapper: flatten all entries from *results* then match."""
    all_entries: List[CronEntry] = []
    for result in results:
        if result.parse_result is not None:
            all_entries.extend(result.parse_result.entries)
    return match_entries(all_entries, templates)
