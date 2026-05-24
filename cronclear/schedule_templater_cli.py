"""CLI command for matching cron entries against schedule templates."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cronclear.schedule_templater import ScheduleTemplate, TemplateReport, match_entries


def build_templater_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser("template", help="Match cron entries against named schedule templates")
    p.add_argument("templates_file", help="JSON file defining schedule templates")
    p.add_argument("--host", dest="hosts", metavar="HOST", action="append", default=[],
                   help="Limit to specific host(s); may be repeated")
    p.add_argument("--unmatched", action="store_true",
                   help="Show only entries that did not match any template")
    p.add_argument("--no-color", action="store_true", help="Disable colored output")
    return p


def _load_templates(path: str) -> list[ScheduleTemplate]:
    data = json.loads(Path(path).read_text())
    return [ScheduleTemplate(**t) for t in data]


def _render_report(report: TemplateReport, unmatched_only: bool, color: bool) -> None:
    RESET = "\033[0m" if color else ""
    BOLD = "\033[1m" if color else ""
    DIM = "\033[2m" if color else ""
    GREEN = "\033[32m" if color else ""
    YELLOW = "\033[33m" if color else ""

    if unmatched_only:
        items = [(None, m) for m in report.unmatched]
        print(f"{BOLD}Unmatched entries: {len(items)}{RESET}")
    else:
        items = [(label, m) for label, matches in report.by_label.items() for m in matches]  # type: ignore[assignment]
        print(f"{BOLD}Template matches: {report.total}  Unmatched: {len(report.unmatched)}{RESET}")

    for label, match in items:
        if label is not None:
            tag = f"{GREEN}[{label}]{RESET} "
        else:
            tag = f"{YELLOW}[unmatched]{RESET} "
        entry = match.entry if hasattr(match, "entry") else match  # type: ignore[union-attr]
        host = getattr(entry, "host", "?")
        print(f"  {tag}{DIM}{host}{RESET}  {entry}")


def run_templater_command(args: argparse.Namespace, report: TemplateReport | None = None) -> int:
    if report is None:
        try:
            templates = _load_templates(args.templates_file)
        except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        # In real usage you'd collect from hosts; here we just return empty.
        report = TemplateReport(matches=[], unmatched=[])

    _render_report(report, getattr(args, "unmatched", False), not getattr(args, "no_color", False))
    return 0 if report.total > 0 or not report.unmatched else 0
