"""CLI sub-command for archiving cron schedules from remote hosts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronclear.cron_collector import CronCollector
from cronclear.schedule_archiver import archive_results, load_archive
from cronclear.ssh_client import SSHConnectionConfig


def build_archiver_parser(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    sub.add_argument("hosts", nargs="+", help="Remote hosts to collect from")
    sub.add_argument("--user", default="root", help="SSH username")
    sub.add_argument("--key-file", default=None, help="Path to SSH private key")
    sub.add_argument(
        "--archive-dir",
        default=".cronclear/archives",
        help="Directory to store archive files",
    )
    sub.add_argument(
        "--list",
        metavar="ARCHIVE_FILE",
        default=None,
        help="List entries from an existing archive file instead of collecting",
    )
    return sub


def run_archiver_command(args: argparse.Namespace) -> int:
    if args.list:
        path = Path(args.list)
        if not path.exists():
            print(f"Archive file not found: {path}", file=sys.stderr)
            return 1
        entries = load_archive(path)
        if not entries:
            print("No entries in archive.")
            return 0
        print(f"{'HOST':<20} {'USER':<12} {'SCHEDULE':<20} COMMAND")
        print("-" * 72)
        for e in entries:
            print(f"{e.host:<20} {e.user:<12} {e.schedule:<20} {e.command}")
        print(f"\nTotal: {len(entries)} entries")
        return 0

    configs = [
        SSHConnectionConfig(host=h, username=args.user, key_file=args.key_file)
        for h in args.hosts
    ]
    collector = CronCollector(configs)
    results = collector.collect_from_hosts()

    report = archive_results(results, Path(args.archive_dir))
    print(f"Archived {report.entry_count} entries from {len(report.hosts)} host(s)")
    print(f"Saved to: {report.path}")
    return 0
