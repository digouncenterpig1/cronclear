"""Suggest schedule improvements based on common patterns and risk scores."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from cronclear.cron_parser import CronEntry
from cronclear.schedule_scorer import score_entry


@dataclass
class Recommendation:
    host: str
    command: str
    current_schedule: str
    suggested_schedule: str
    reason: str

    def __str__(self) -> str:
        return (
            f"[{self.host}] {self.command!r}: "
            f"{self.current_schedule!r} -> {self.suggested_schedule!r} ({self.reason})"
        )


@dataclass
class RecommendationReport:
    recommendations: List[Recommendation] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.recommendations)

    def by_host(self, host: str) -> List[Recommendation]:
        return [r for r in self.recommendations if r.host == host]


_EVERY_MINUTE = "* * * * *"
_EVERY_MINUTE_ALT = "*/1 * * * *"
_HIGH_FREQ_STEPS = {"*/1", "*/2", "*/3", "*/4", "*/5"}


def _suggest(entry: CronEntry) -> Optional[Recommendation]:
    """Return a Recommendation if a better schedule exists, else None."""
    scored = score_entry(entry)
    sched = entry.schedule
    parts = sched.split()

    if sched in (_EVERY_MINUTE, _EVERY_MINUTE_ALT):
        return Recommendation(
            host=entry.host or "",
            command=entry.command,
            current_schedule=sched,
            suggested_schedule="*/5 * * * *",
            reason="every-minute polling is noisy; consider every 5 minutes",
        )

    if len(parts) == 5 and parts[0] in _HIGH_FREQ_STEPS and parts[1] == "*":
        return Recommendation(
            host=entry.host or "",
            command=entry.command,
            current_schedule=sched,
            suggested_schedule=f"{parts[0]} * * * *",
            reason="consider anchoring to a fixed offset to reduce thundering herd",
        )

    if scored.total_score >= 8 and len(parts) == 5 and parts[1] == "*":
        return Recommendation(
            host=entry.host or "",
            command=entry.command,
            current_schedule=sched,
            suggested_schedule=f"{parts[0]} 2 * * *",
            reason="high-risk schedule; consider running during off-peak hours",
        )

    return None


def recommend(entries: List[CronEntry]) -> RecommendationReport:
    recs: List[Recommendation] = []
    for entry in entries:
        if entry.is_shortcut():
            continue
        rec = _suggest(entry)
        if rec:
            recs.append(rec)
    return RecommendationReport(recommendations=recs)
