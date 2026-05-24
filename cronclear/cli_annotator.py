"""CLI sub-command: annotate cron entries with human-readable schedule labels."""
import argparse
import sys
from typing import List

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_annotator import annotate_entries, AnnotationReport


def build_annotator_parser(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--label", metavar="LABEL", help="filter output to a specific label")
    sub.add_argument("--no-color", action="store_true", help="disable colour output")


def _render_report(report: AnnotationReport, label_filter: str = "", color: bool = True) -> None:
    RESET = "\033[0m" if color else ""
    BOLD = "\033[1m" if color else ""
    DIM = "\033[2m" if color else ""

    entries = report.entries
    if label_filter:
        entries = [a for a in entries if a.label == label_filter]

    if not entries:
        print("No annotated entries found.")
        return

    col_w = max(len(a.label) for a in entries) + 2
    print(f"{BOLD}{'Label':<{col_w}}  {'Host':<18}  Command{RESET}")
    print("-" * 72)
    for ann in entries:
        note_str = f"  {DIM}# {ann.note}{RESET}" if ann.note else ""
        host = getattr(ann.entry, "host", "unknown")
        print(f"{ann.label:<{col_w}}  {host:<18}  {ann.entry.command}{note_str}")


def run_annotator_command(
    results: List[CollectionResult],
    args: argparse.Namespace,
) -> int:
    all_entries = [e for r in results for e in r.entries]
    if not all_entries:
        print("No cron entries to annotate.")
        return 0

    report = annotate_entries(all_entries)
    label_filter = getattr(args, "label", "") or ""
    color = not getattr(args, "no_color", False)
    _render_report(report, label_filter=label_filter, color=color)
    return 0
