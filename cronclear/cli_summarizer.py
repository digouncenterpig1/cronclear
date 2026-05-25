"""CLI command to display a digest summary of cron schedules."""
from __future__ import annotations

import argparse
from typing import List

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_summarizer import DigestReport, HostSummary, summarize_results


def build_summarizer_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = sub.add_parser("summarize", help="Show a digest summary of cron schedules")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    p.add_argument(
        "--min-jobs",
        type=int,
        default=0,
        help="Only show hosts with at least N jobs",
    )
    return p


def _render_host_summary(summary: HostSummary, no_color: bool = False) -> None:
    bold = "" if no_color else "\033[1m"
    reset = "" if no_color else "\033[0m"
    cyan = "" if no_color else "\033[36m"

    print(f"{bold}{cyan}{summary.host}{reset}")
    print(f"  Jobs            : {summary.total_jobs}")
    print(f"  Unique schedules: {summary.unique_schedules}")
    if summary.most_common_schedule:
        print(f"  Most common     : {summary.most_common_schedule}")


def _render_report(report: DigestReport, no_color: bool = False) -> None:
    print(f"Hosts : {report.total_hosts}")
    print(f"Jobs  : {report.total_jobs}")
    print(f"Unique schedules (global): {report.global_unique_schedules}")
    print(f"Avg jobs/host: {report.average_jobs_per_host:.1f}")
    print()
    for hs in report.host_summaries:
        _render_host_summary(hs, no_color=no_color)
        print()


def run_summarizer_command(
    args: argparse.Namespace,
    results: List[CollectionResult],
) -> int:
    report = summarize_results(results)

    if args.min_jobs > 0:
        report.host_summaries = [
            s for s in report.host_summaries if s.total_jobs >= args.min_jobs
        ]
        report.total_hosts = len(report.host_summaries)

    if report.total_hosts == 0:
        print("No hosts with cron jobs found.")
        return 0

    _render_report(report, no_color=getattr(args, "no_color", False))
    return 0
