"""CLI subcommand: group cron entries by schedule or command prefix."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_grouper import (
    group_by_schedule,
    group_by_command_prefix,
    unique_schedules,
)


def build_grouper_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser("group", help="Group cron entries by schedule or command prefix")
    p.add_argument(
        "--by",
        choices=["schedule", "command"],
        default="schedule",
        help="Grouping strategy (default: schedule)",
    )
    p.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="N",
        help="Path depth for command grouping (default: 1)",
    )
    p.add_argument(
        "--list-schedules",
        action="store_true",
        help="Print unique schedule expressions and exit",
    )
    return p


def _render_schedule_groups(results: List[CollectionResult]) -> None:
    groups = group_by_schedule(results)
    if not groups:
        print("No cron entries found.")
        return
    for sched, grp in sorted(groups.items()):
        print(f"[{sched}]  hosts={grp.host_count}  jobs={grp.command_count}")
        for entry in grp.entries:
            host_tag = f"({entry.host}) " if entry.host else ""
            print(f"    {host_tag}{entry.command}")


def _render_command_groups(results: List[CollectionResult], depth: int) -> None:
    groups = group_by_command_prefix(results, depth=depth)
    if not groups:
        print("No cron entries found.")
        return
    for prefix, entries in sorted(groups.items()):
        print(f"[{prefix}]  jobs={len(entries)}")
        for entry in entries:
            host_tag = f"({entry.host}) " if entry.host else ""
            print(f"    {host_tag}{entry.schedule}  {entry.command}")


def run_grouper_command(
    args: argparse.Namespace,
    results: List[CollectionResult],
) -> int:
    if args.list_schedules:
        for s in unique_schedules(results):
            print(s)
        return 0

    if args.by == "schedule":
        _render_schedule_groups(results)
    else:
        _render_command_groups(results, depth=args.depth)

    return 0
