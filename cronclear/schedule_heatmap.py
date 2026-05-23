"""Build hour-of-day / day-of-week heatmap data from cron entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from cronclear.cron_parser import CronEntry

# Ordered day labels
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
HOURS = list(range(24))


@dataclass
class HeatmapData:
    """Aggregated hit counts indexed by [day_index][hour]."""

    # counts[day_index][hour] -> number of jobs that fire at that slot
    counts: Dict[int, Dict[int, int]] = field(
        default_factory=lambda: {d: {h: 0 for h in HOURS} for d in range(7)}
    )

    def total_hits(self) -> int:
        return sum(v for day in self.counts.values() for v in day.values())

    def busiest_hour(self) -> int:
        """Return the hour (0-23) with the most cumulative hits across all days."""
        hour_totals: Dict[int, int] = {h: 0 for h in HOURS}
        for day_counts in self.counts.values():
            for h, cnt in day_counts.items():
                hour_totals[h] += cnt
        return max(hour_totals, key=lambda h: hour_totals[h])

    def busiest_day(self) -> str:
        """Return the day name with the most cumulative hits."""
        day_totals = {
            d: sum(self.counts[d].values()) for d in range(7)
        }
        idx = max(day_totals, key=lambda d: day_totals[d])
        return DAYS[idx]


def _expand_field(field_str: str, min_val: int, max_val: int) -> List[int]:
    """Expand a cron field string into a list of integer values."""
    if field_str == "*":
        return list(range(min_val, max_val + 1))
    values: List[int] = []
    for part in field_str.split(","):
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            start = min_val if base == "*" else int(base.split("-")[0])
            end = max_val if base == "*" else (int(base.split("-")[1]) if "-" in base else start)
            values.extend(range(start, end + 1, step))
        elif "-" in part:
            a, b = part.split("-", 1)
            values.extend(range(int(a), int(b) + 1))
        else:
            values.append(int(part))
    return values


def build_heatmap(entries: List[CronEntry]) -> HeatmapData:
    """Aggregate cron entries into a HeatmapData object."""
    heatmap = HeatmapData()
    for entry in entries:
        if entry.is_shortcut():
            # shortcuts fire once — treat as all hours/days unknown, skip
            continue
        fields = entry.schedule.split()
        if len(fields) < 5:
            continue
        _, hour_f, _, _, dow_f = fields[:5]
        try:
            hours = _expand_field(hour_f, 0, 23)
            days = _expand_field(dow_f, 0, 6)
        except (ValueError, IndexError):
            continue
        for d in days:
            for h in hours:
                heatmap.counts[d][h] += 1
    return heatmap
