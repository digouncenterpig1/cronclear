"""CLI sub-command for searching cron entries."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_search import SearchReport, search_entries


def build_search_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = subparsers.add_parser("search", help="Search cron entries by pattern")
    p.add_argument("query", help="Regex or plain-text search pattern")
    p.add_argument(
        "--field",
        choices=["command", "schedule", "user"],
        default=None,
        help="Restrict search to a specific field (default: all)",
    )
    p.add_argument(
        "--case-sensitive",
        action="store_true",
        default=False,
        help="Enable case-sensitive matching",
    )
    return p


def _render_search(report: SearchReport) -> None:
    if report.total == 0:
        print(f"No matches found for '{report.query}'.")
        return

    print(f"Found {report.total} match(es) for '{report.query}' across {len(report.hosts)} host(s):\n")
    current_host = None
    for sr in report.results:
        if sr.host != current_host:
            current_host = sr.host
            print(f"  [{current_host}]")
        tag = f"({sr.matched_field})"
        print(f"    {str(sr.entry.schedule):<30}  {sr.entry.command}  {tag}")
    print()


def run_search_command(
    args: argparse.Namespace,
    collection_results: List[CollectionResult],
) -> int:
    try:
        report = search_entries(
            collection_results,
            args.query,
            field=args.field,
            case_sensitive=args.case_sensitive,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _render_search(report)
    return 0
