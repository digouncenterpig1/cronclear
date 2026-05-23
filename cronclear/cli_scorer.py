"""CLI sub-command: score — rank cron entries by risk score."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_scorer import ScoredEntry, score_entries

_RISK_COLORS = {
    "high": "\033[91m",   # red
    "medium": "\033[93m", # yellow
    "low": "\033[92m",    # green
}
_RESET = "\033[0m"


def build_score_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:  # noqa: SLF001
    p = subparsers.add_parser(
        "score",
        help="Rank cron entries by risk/interest score.",
    )
    p.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        metavar="N",
        help="Only show entries with score >= N (default: 0).",
    )
    p.add_argument(
        "--risk",
        choices=["low", "medium", "high"],
        default=None,
        help="Filter by risk label.",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colour output.",
    )
    return p


def _render_scored(scored: List[ScoredEntry], no_color: bool = False) -> str:
    lines: list[str] = []
    for se in scored:
        color = "" if no_color else _RISK_COLORS.get(se.risk_label, "")
        reset = "" if no_color else _RESET
        reasons = ", ".join(se.reasons) if se.reasons else "—"
        lines.append(
            f"{color}[{se.risk_label.upper():6s}] score={se.score:5.1f}{reset}"
            f"  host={se.entry.host}  user={se.entry.user}"
            f"  schedule={se.entry.schedule!r}"
            f"  cmd={se.entry.command!r}"
            f"  reasons: {reasons}"
        )
    return "\n".join(lines)


def run_score_command(
    args: argparse.Namespace,
    results: List[CollectionResult],
    out=sys.stdout,
) -> int:
    all_entries = [
        entry
        for result in results
        for entry in result.entries
    ]

    if not all_entries:
        print("No cron entries found.", file=out)
        return 0

    scored = score_entries(all_entries)

    # apply filters
    if args.min_score > 0:
        scored = [s for s in scored if s.score >= args.min_score]
    if args.risk:
        scored = [s for s in scored if s.risk_label == args.risk]

    if not scored:
        print("No entries match the given filters.", file=out)
        return 0

    print(f"Scored {len(scored)} entr{'y' if len(scored) == 1 else 'ies'}:", file=out)
    print(_render_scored(scored, no_color=getattr(args, "no_color", False)), file=out)
    return 0
