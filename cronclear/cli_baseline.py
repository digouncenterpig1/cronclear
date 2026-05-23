"""CLI sub-commands for baseline capture and comparison."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronclear.cron_collector import CronCollector
from cronclear.schedule_baseline import (
    compare_to_baseline,
    load_baseline,
    save_baseline,
)
from cronclear.ssh_client import SSHConnectionConfig

DEFAULT_BASELINE_PATH = Path(".cronclear_baseline.json")


def build_baseline_parser(parent: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = parent.add_parser("baseline", help="Manage cron schedule baselines")
    sub = p.add_subparsers(dest="baseline_cmd", required=True)

    cap = sub.add_parser("capture", help="Save current schedules as baseline")
    cap.add_argument("hosts", nargs="+", help="Remote hosts to capture from")
    cap.add_argument("--user", default="root")
    cap.add_argument("--key-file", dest="key_file", default=None)
    cap.add_argument("--output", default=str(DEFAULT_BASELINE_PATH))

    cmp = sub.add_parser("compare", help="Compare current schedules against baseline")
    cmp.add_argument("hosts", nargs="+")
    cmp.add_argument("--user", default="root")
    cmp.add_argument("--key-file", dest="key_file", default=None)
    cmp.add_argument("--baseline", default=str(DEFAULT_BASELINE_PATH))


def _collect_all_entries(hosts: list, user: str, key_file):
    entries = []
    for host in hosts:
        cfg = SSHConnectionConfig(host=host, username=user, key_file=key_file)
        collector = CronCollector(cfg)
        result = collector.collect_from_host(host)
        entries.extend(result.entries)
    return entries


def run_baseline_command(args: argparse.Namespace) -> int:
    if args.baseline_cmd == "capture":
        entries = _collect_all_entries(args.hosts, args.user, args.key_file)
        out = Path(args.output)
        save_baseline(entries, out)
        print(f"Baseline saved to {out} ({len(entries)} entries).")
        return 0

    if args.baseline_cmd == "compare":
        baseline_path = Path(args.baseline)
        baseline = load_baseline(baseline_path)
        if baseline is None:
            print(f"No baseline found at {baseline_path}. Run 'capture' first.", file=sys.stderr)
            return 1
        entries = _collect_all_entries(args.hosts, args.user, args.key_file)
        report = compare_to_baseline(entries, baseline)
        print(report.summary_line())
        if report.added:
            print("  Added:")
            for e in report.added:
                print(f"    [{e.host}] {e.user}: {e.raw}")
        if report.removed:
            print("  Removed:")
            for e in report.removed:
                print(f"    [{e.host}] {e.user}: {e.raw}")
        return 1 if report.has_changes else 0

    return 0
