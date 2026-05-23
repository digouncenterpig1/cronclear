"""Parse and represent crontab entries from raw crontab output."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CronEntry:
    """Represents a single crontab entry."""

    minute: str
    hour: str
    day_of_month: str
    month: str
    day_of_week: str
    command: str
    raw_line: str
    user: Optional[str] = None
    host: Optional[str] = None

    @property
    def schedule(self) -> str:
        return f"{self.minute} {self.hour} {self.day_of_month} {self.month} {self.day_of_week}"

    @property
    def is_shortcut(self) -> bool:
        """Return True if this entry uses an @ shortcut (e.g. @reboot, @daily)."""
        return self.minute.startswith("@")

    def __str__(self) -> str:
        user_info = f"{self.user}@" if self.user else ""
        host_info = self.host or "localhost"
        return f"[{user_info}{host_info}] {self.schedule}  {self.command}"


@dataclass
class ParseResult:
    """Result of parsing a crontab output block."""

    entries: List[CronEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_output: str = ""


def parse_crontab(output: str, user: Optional[str] = None, host: Optional[str] = None) -> ParseResult:
    """Parse raw crontab -l output into CronEntry objects.

    Args:
        output: Raw text from `crontab -l`.
        user: Optional username to attach to each entry.
        host: Optional hostname to attach to each entry.

    Returns:
        ParseResult with parsed entries and any errors encountered.
    """
    result = ParseResult(raw_output=output)

    for lineno, line in enumerate(output.splitlines(), start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        # Handle @reboot and other @ shortcuts
        if stripped.startswith("@"):
            parts = stripped.split(None, 1)
            if len(parts) < 2:
                result.errors.append(f"Line {lineno}: malformed shortcut entry: {line!r}")
                continue
            entry = CronEntry(
                minute=parts[0],
                hour="",
                day_of_month="",
                month="",
                day_of_week="",
                command=parts[1],
                raw_line=line,
                user=user,
                host=host,
            )
            result.entries.append(entry)
            continue

        parts = stripped.split(None, 5)
        if len(parts) < 6:
            result.errors.append(f"Line {lineno}: could not parse entry: {line!r}")
            continue

        entry = CronEntry(
            minute=parts[0],
            hour=parts[1],
            day_of_month=parts[2],
            month=parts[3],
            day_of_week=parts[4],
            command=parts[5],
            raw_line=line,
            user=user,
            host=host,
        )
        result.entries.append(entry)

    return result
