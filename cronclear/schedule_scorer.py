"""Score cron entries by risk/interest level based on frequency, timing, and patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cronclear.cron_parser import CronEntry

# Weights used to compute a composite risk score (0-100)
_FREQ_WEIGHT = 0.4
_ODD_HOUR_WEIGHT = 0.3
_ROOT_WEIGHT = 0.2
_SHORTCUT_WEIGHT = 0.1

ODD_HOURS = set(range(0, 6))  # midnight to 5 AM


@dataclass
class ScoredEntry:
    entry: CronEntry
    score: float  # 0.0 – 100.0
    reasons: List[str] = field(default_factory=list)

    @property
    def risk_label(self) -> str:
        if self.score >= 70:
            return "high"
        if self.score >= 40:
            return "medium"
        return "low"


def _frequency_score(entry: CronEntry) -> tuple[float, list[str]]:
    """Higher frequency → higher score contribution."""
    reasons: list[str] = []
    if entry.is_shortcut:
        # shortcuts like @reboot are hard to predict
        reasons.append("uses schedule shortcut")
        return 50.0, reasons
    minute = entry.schedule.split()[0]
    if minute == "*":
        reasons.append("runs every minute")
        return 100.0, reasons
    if "/" in minute:
        try:
            interval = int(minute.split("/")[1])
            if interval <= 5:
                reasons.append(f"runs every {interval} minute(s)")
                return 80.0, reasons
        except ValueError:
            pass
    return 10.0, reasons


def _odd_hour_score(entry: CronEntry) -> tuple[float, list[str]]:
    """Jobs running in odd hours score higher."""
    if entry.is_shortcut:
        return 0.0, []
    parts = entry.schedule.split()
    if len(parts) < 2:
        return 0.0, []
    hour_field = parts[1]
    reasons: list[str] = []
    if hour_field == "*":
        return 0.0, []
    try:
        hour = int(hour_field)
        if hour in ODD_HOURS:
            reasons.append(f"scheduled at odd hour ({hour:02d}:xx)")
            return 100.0, reasons
    except ValueError:
        pass
    return 0.0, []


def score_entry(entry: CronEntry) -> ScoredEntry:
    freq_s, freq_r = _frequency_score(entry)
    odd_s, odd_r = _odd_hour_score(entry)

    root_score = 100.0 if entry.user == "root" else 0.0
    root_reasons = ["runs as root"] if entry.user == "root" else []

    shortcut_score = 100.0 if entry.is_shortcut else 0.0
    shortcut_reasons = ["non-standard schedule shortcut"] if entry.is_shortcut else []

    composite = (
        freq_s * _FREQ_WEIGHT
        + odd_s * _ODD_HOUR_WEIGHT
        + root_score * _ROOT_WEIGHT
        + shortcut_score * _SHORTCUT_WEIGHT
    )
    all_reasons = freq_r + odd_r + root_reasons + shortcut_reasons
    return ScoredEntry(entry=entry, score=round(composite, 1), reasons=all_reasons)


def score_entries(entries: List[CronEntry]) -> List[ScoredEntry]:
    """Return entries sorted by score descending."""
    scored = [score_entry(e) for e in entries]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored
