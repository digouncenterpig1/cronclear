"""CLI entry point for the schedule comparator."""
from __future__ import annotations
import argparse
from typing import List, Tuple

from cronclear.schedule_comparator import ComparisonReport, HostComparison


def build_comparator_parser(parent: argparse._SubParsersAction) -> argparse.ArgumentParser:
    p = parent.add_parser("compare", help="Compare cron schedules between host pairs")
    p.add_argument("--pair", metavar="A:B", action="append", dest="pairs",
                   required=True, help="Host pair to compare, e.g. web1:web2")
    p.add_argument("--no-color", action="store_true", default=False)
    return p


def _parse_pairs(raw: List[str]) -> List[Tuple[str, str]]:
    pairs = []
    for item in raw:
        parts = item.split(":", 1)
        if len(parts) == 2:
            pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def _render_comparison(comp: HostComparison, no_color: bool = False) -> None:
    tag = "[DIFF]" if comp.has_differences else "[SAME]"
    print(f"{tag} {comp.host_a} vs {comp.host_b}")
    for e in comp.only_in_a:
        print(f"  < {e.schedule}  {e.command}")
    for e in comp.only_in_b:
        print(f"  > {e.schedule}  {e.command}")
    if not comp.has_differences:
        print(f"  (shared {len(comp.shared)} jobs)")


def run_comparator_command(args: argparse.Namespace, report: ComparisonReport) -> int:
    pairs = _parse_pairs(args.pairs)
    if not pairs:
        print("No valid pairs provided.")
        return 1

    if not report.comparisons:
        print("No matching host pairs found in results.")
        return 1

    for comp in report.comparisons:
        _render_comparison(comp, no_color=args.no_color)

    differing = len(report.differing_pairs)
    print(f"\n{report.total_pairs} pair(s) compared, {differing} with differences.")
    return 0 if differing == 0 else 1
