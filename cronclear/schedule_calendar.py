"""Build a weekly calendar view of cron job activity."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

from cronclear.cron_parser import CronEntry

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
HOURS = list(range(24))


@dataclass
class CalendarCell:
    day: str
    hour: int
    entries: List[CronEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)


@dataclass
class WeeklyCalendar:
    """7-day x 24-hour grid of scheduled cron entries."""
    cells: Dict[str, Dict[int, CalendarCell]] = field(default_factory=dict)

    def get(self, day: str, hour: int) -> CalendarCell:
        return self.cells.get(day, {}).get(hour, CalendarCell(day=day, hour=hour))

    def busiest_slot(self) -> CalendarCell:
        best: CalendarCell = CalendarCell(day="Mon", hour=0)
        for day_map in self.cells.values():
            for cell in day_map.values():
                if cell.count > best.count:
                    best = cell
        return best

    def total_slots_used(self) -> int:
        return sum(
            1
            for day_map in self.cells.values()
            for cell in day_map.values()
            if cell.count > 0
        )


def _expand_field(field_str: str, min_val: int, max_val: int) -> List[int]:
    """Return list of integers the cron field resolves to."""
    if field_str == "*":
        return list(range(min_val, max_val + 1))
    results: List[int] = []
    for part in field_str.split(","):
        if "/" in part:
            base, step = part.split("/", 1)
            rng = range(min_val, max_val + 1) if base == "*" else range(*[int(x) for x in base.split("-", 1)], 1)
            results.extend(rng[::int(step)])
        elif "-" in part:
            lo, hi = part.split("-", 1)
            results.extend(range(int(lo), int(hi) + 1))
        else:
            results.append(int(part))
    return results


def build_calendar(entries: List[CronEntry]) -> WeeklyCalendar:
    """Populate a WeeklyCalendar from a list of CronEntry objects."""
    cal = WeeklyCalendar(cells={day: {h: CalendarCell(day=day, hour=h) for h in HOURS} for day in DAYS})
    for entry in entries:
        if entry.is_shortcut():
            continue
        parts = entry.schedule.split()
        if len(parts) < 5:
            continue
        _, hour_f, _, _, dow_f = parts[:5]
        hours = _expand_field(hour_f, 0, 23)
        # cron dow: 0/7=Sun,1=Mon,...,6=Sat
        raw_days = _expand_field(dow_f, 0, 7)
        mapped: List[str] = []
        for d in raw_days:
            idx = (d - 1) % 7  # shift so Mon=0
            mapped.append(DAYS[idx])
        for day in set(mapped):
            for h in hours:
                cal.cells[day][h].entries.append(entry)
    return cal
