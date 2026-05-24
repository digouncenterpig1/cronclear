"""CLI sub-command: recommend schedule improvements."""
from __future__ import annotations
import argparse
from typing import List
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_recommender import RecommendationReport, recommend


def build_recommender_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser("recommend", help="suggest schedule improvements")
    p.add_argument("--host", metavar="HOST", help="filter recommendations to a single host")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    return p


def _render_report(report: RecommendationReport, host_filter: str | None, color: bool) -> None:
    recs = report.recommendations
    if host_filter:
        recs = [r for r in recs if r.host == host_filter]

    if not recs:
        print("No recommendations — schedules look fine.")
        return

    print(f"Recommendations ({len(recs)}):")
    for rec in recs:
        host_tag = f"[{rec.host}] " if rec.host else ""
        arrow = "->" if not color else "\033[33m->\033[0m"
        print(
            f"  {host_tag}{rec.command!r}\n"
            f"    {rec.current_schedule!r} {arrow} {rec.suggested_schedule!r}\n"
            f"    Reason: {rec.reason}"
        )


def run_recommender_command(
    args: argparse.Namespace,
    results: List[CollectionResult],
) -> int:
    all_entries = [e for r in results for e in r.entries]
    report = recommend(all_entries)
    _render_report(report, getattr(args, "host", None), not getattr(args, "no_color", False))
    return 0
