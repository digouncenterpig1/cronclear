"""CLI sub-command: render a weekly calendar heatmap of cron schedules."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronclear.cron_collector import CronCollector
from cronclear.schedule_calendar import DAYS, HOURS, WeeklyCalendar, build_calendar
from cronclear.ssh_client import SSHConnectionConfig

_SHADE = [" ", "░", "▒", "▓", "█"]


def _shade(count: int) -> str:
    if count == 0:
        return _SHADE[0]
    if count <= 2:
        return _SHADE[1]
    if count <= 5:
        return _SHADE[2]
    if count <= 10:
        return _SHADE[3]
    return _SHADE[4]


def _render_calendar(cal: WeeklyCalendar) -> None:
    header = "     " + "".join(f"{h:02d} " for h in HOURS)
    print(header)
    for day in DAYS:
        row = f"{day}  " + "".join(f" {_shade(cal.get(day, h).count)}  " for h in HOURS)
        print(row)
    busiest = cal.busiest_slot()
    print(f"\nBusiest slot: {busiest.day} {busiest.hour:02d}:00 ({busiest.count} jobs)")
    print(f"Active slots: {cal.total_slots_used()} / {len(DAYS) * 24}")


def build_calendar_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser("calendar", help="Show weekly calendar heatmap of cron jobs")
    p.add_argument("hosts", nargs="+", help="Remote hosts to collect from")
    p.add_argument("--user", default="root")
    p.add_argument("--key-file", dest="key_file", default=None)
    p.add_argument("--password", default=None)
    return p


def run_calendar_command(args: argparse.Namespace) -> int:
    configs: List[SSHConnectionConfig] = [
        SSHConnectionConfig(
            host=h,
            username=args.user,
            key_file=args.key_file,
            password=args.password,
        )
        for h in args.hosts
    ]
    collector = CronCollector(configs)
    results = collector.collect_from_hosts()
    all_entries = [e for r in results for e in r.entries]
    if not all_entries:
        print("No cron entries found.", file=sys.stderr)
        return 1
    cal = build_calendar(all_entries)
    _render_calendar(cal)
    return 0
