"""Format and render analysis reports to the terminal."""

from typing import List
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich import box

from cronclear.schedule_analyzer import AnalysisReport, ScheduleSummary

console = Console()


def _fmt_next_run(dt: datetime | None) -> str:
    if dt is None:
        return "[red]N/A[/red]"
    delta = dt - datetime.now()
    minutes = int(delta.total_seconds() / 60)
    if minutes < 0:
        return "[red]overdue[/red]"
    if minutes < 60:
        return f"[yellow]in {minutes}m[/yellow]"
    hours = minutes // 60
    return f"[green]in {hours}h {minutes % 60}m[/green]"


def _fmt_frequency(s: ScheduleSummary) -> str:
    """Format the frequency string, highlighting high-frequency jobs in bold red."""
    freq_str = f"{s.frequency_per_day:.1f}"
    if s.is_frequent:
        return f"[bold red]{freq_str}[/bold red]"
    return freq_str


def render_summary_table(report: AnalysisReport) -> None:
    table = Table(
        title=f"Cron Schedule Report ({report.total_jobs} jobs)",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Host", style="cyan", no_wrap=True)
    table.add_column("User", style="magenta")
    table.add_column("Schedule", style="blue")
    table.add_column("Next Run")
    table.add_column("Freq/day", justify="right")
    table.add_column("Command", style="white", max_width=40)

    for s in report.summaries:
        table.add_row(
            s.host,
            s.user,
            s.schedule,
            _fmt_next_run(s.next_run),
            _fmt_frequency(s),
            s.command,
        )

    console.print(table)


def render_duplicates(report: AnalysisReport) -> None:
    if not report.duplicates:
        console.print("[green]No duplicate commands found.[/green]")
        return

    console.print(f"\n[bold yellow]Duplicate commands ({len(report.duplicates)}):[/bold yellow]")
    for cmd, entries in report.duplicates.items():
        hosts = ", ".join(f"{e.host}({e.user})" for e in entries)
        console.print(f"  [white]{cmd[:60]}[/white] → {hosts}")


def render_frequent_jobs(report: AnalysisReport) -> None:
    if not report.frequent_jobs:
        return
    console.print(f"\n[bold red]High-frequency jobs (>24/day): {len(report.frequent_jobs)}[/bold red]")
    for s in report.frequent_jobs:
        console.print(f"  [{s.host}] {s.user}: {s.schedule} → {s.command[:50]}")


def render_stats(report: AnalysisReport) -> None:
    """Print a brief stats footer with host and user counts."""
    hosts = {s.host for s in report.summaries}
    users = {s.user for s in report.summaries}
    console.print(
        f"\n[dim]Hosts: {len(hosts)}  |  Users: {len(users)}  |  "
        f"Duplicates: {len(report.duplicates)}  |  "
        f"High-frequency: {len(report.frequent_jobs)}[/dim]"
    )


def render_report(report: AnalysisReport) -> None:
    render_summary_table(report)
    render_duplicates(report)
    render_frequent_jobs(report)
    render_stats(report)
