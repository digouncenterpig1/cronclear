"""CLI sub-command: lint — check cron entries for common issues."""
from __future__ import annotations

import argparse
from typing import List

from cronclear.cron_collector import CollectionResult
from cronclear.schedule_linter import LintReport, lint_results


def build_linter_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:  # type: ignore[type-arg]
    p = sub.add_parser("lint", help="Lint cron entries for suspicious or broken patterns")
    p.add_argument("--code", metavar="CODE", help="Filter output to a specific issue code")
    p.add_argument("--no-color", action="store_true", help="Disable coloured output")
    return p


_CODE_COLORS = {
    "NOISY": "\033[33m",
    "RISKY_CMD": "\033[31m",
    "EMPTY_CMD": "\033[35m",
    "MALFORMED": "\033[36m",
}
_RESET = "\033[0m"


def _render_report(report: LintReport, code_filter: str | None, color: bool) -> None:
    issues = report.issues
    if code_filter:
        issues = [i for i in issues if i.code == code_filter]

    if not issues:
        print("No lint issues found.")
        return

    print(f"Found {len(issues)} lint issue(s):\n")
    for issue in issues:
        prefix = ""
        suffix = ""
        if color:
            prefix = _CODE_COLORS.get(issue.code, "")
            suffix = _RESET if prefix else ""
        print(f"  {prefix}{issue}{suffix}")


def run_linter_command(
    args: argparse.Namespace,
    results: List[CollectionResult],
) -> int:
    report = lint_results(results)
    _render_report(
        report,
        code_filter=getattr(args, "code", None),
        color=not getattr(args, "no_color", False),
    )
    return 1 if report.has_issues() else 0
