"""CLI sub-command: cronclear snapshot-diff"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from cronclear.schedule_watcher import load_snapshot
from cronclear.schedule_snapshot_diff import diff_snapshots, SnapshotDiffReport


def build_snapshot_diff_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser(
        "snapshot-diff",
        help="Diff two snapshot files and show cron schedule changes",
    )
    p.add_argument("old_snapshot", help="Path to the older snapshot JSON file")
    p.add_argument("new_snapshot", help="Path to the newer snapshot JSON file")
    p.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    return p


def _render_report(report: SnapshotDiffReport, color: bool = True) -> None:
    if not report.has_any_changes:
        print("No changes detected between snapshots.")
        return

    for line in report.summary_lines():
        if color:
            if line.startswith("[+"):
                print(f"\033[32m{line}\033[0m")
            elif line.startswith("[-"):
                print(f"\033[31m{line}\033[0m")
            else:
                print(f"\033[33m{line}\033[0m")
        else:
            print(line)

    print()
    print(
        f"Summary: +{report.total_added} added, -{report.total_removed} removed"
        f", {len(report.hosts_added)} new hosts, {len(report.hosts_removed)} gone hosts"
    )


def run_snapshot_diff_command(args: argparse.Namespace) -> int:
    old_snap = load_snapshot(args.old_snapshot)
    new_snap = load_snapshot(args.new_snapshot)

    if new_snap is None:
        print(f"Error: cannot load new snapshot from {args.new_snapshot}", file=sys.stderr)
        return 1

    report = diff_snapshots(old_snap, new_snap)
    _render_report(report, color=not args.no_color)
    return 0 if not report.has_any_changes else 2
