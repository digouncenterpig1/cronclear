"""Human-readable formatting helpers for cron schedule expressions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cronclear.cron_parser import CronEntry

_SHORTCUTS = {
    "@reboot": "At system reboot",
    "@yearly": "Once a year (Jan 1, midnight)",
    "@annually": "Once a year (Jan 1, midnight)",
    "@monthly": "Once a month (1st, midnight)",
    "@weekly": "Once a week (Sunday, midnight)",
    "@daily": "Once a day (midnight)",
    "@midnight": "Once a day (midnight)",
    "@hourly": "Once an hour (top of hour)",
}

_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


@dataclass
class FormattedSchedule:
    raw: str
    human: str
    is_shortcut: bool

    def __str__(self) -> str:
        return self.human


def _describe_field(value: str, unit: str, names: Optional[list] = None) -> str:
    if value == "*":
        return f"every {unit}"
    if value.startswith("*/"):
        step = value[2:]
        return f"every {step} {unit}s"
    if "-" in value and "/" not in value:
        lo, hi = value.split("-", 1)
        if names:
            lo_n = names[int(lo) % len(names)]
            hi_n = names[int(hi) % len(names)]
            return f"{lo_n}–{hi_n}"
        return f"{lo}–{hi}"
    if "," in value:
        parts = value.split(",")
        if names:
            parts = [names[int(p) % len(names)] for p in parts]
        return ", ".join(parts)
    if names:
        idx = int(value) % len(names)
        return names[idx]
    return value


def format_schedule(entry: CronEntry) -> FormattedSchedule:
    """Return a FormattedSchedule with a human-readable description."""
    raw = str(entry.schedule)

    if entry.is_shortcut():
        human = _SHORTCUTS.get(raw.lower(), raw)
        return FormattedSchedule(raw=raw, human=human, is_shortcut=True)

    parts = raw.split()
    if len(parts) != 5:
        return FormattedSchedule(raw=raw, human=raw, is_shortcut=False)

    minute, hour, dom, month, dow = parts

    minute_str = _describe_field(minute, "minute")
    hour_str = _describe_field(hour, "hour")
    dom_str = _describe_field(dom, "day-of-month")
    month_str = _describe_field(month, "month", _MONTHS)
    dow_str = _describe_field(dow, "day", _DAYS)

    if dom == "*" and dow == "*":
        time_part = f"at {hour_str}:{minute_str}"
        if month == "*":
            human = f"Daily {time_part}"
        else:
            human = f"Monthly ({month_str}) {time_part}"
    elif dow != "*":
        human = f"Every {dow_str} at {hour_str}:{minute_str}"
    else:
        human = f"On day {dom_str} of {month_str} at {hour_str}:{minute_str}"

    return FormattedSchedule(raw=raw, human=human, is_shortcut=False)
