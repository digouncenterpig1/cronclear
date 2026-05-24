"""Tests for schedule_templater module."""

import pytest
from unittest.mock import MagicMock
from cronclear.schedule_templater import (
    ScheduleTemplate,
    TemplateMatch,
    TemplateReport,
    diff_entries,
)


def _entry(schedule: str, command: str, host: str = "host1", user: str = "root"):
    """Create a minimal fake CronEntry."""
    e = MagicMock()
    e.schedule = schedule
    e.command = command
    e.host = host
    e.user = user
    e.__str__ = lambda self: f"{schedule} {command}"
    return e


# ---------------------------------------------------------------------------
# ScheduleTemplate.matches
# ---------------------------------------------------------------------------

class TestScheduleTemplateMatches:
    def test_matches_exact_schedule_and_pattern(self):
        tmpl = ScheduleTemplate(name="daily-backup", schedule="0 2 * * *", command_pattern="backup")
        entry = _entry("0 2 * * *", "/usr/bin/backup.sh")
        assert tmpl.matches(entry)

    def test_no_match_wrong_schedule(self):
        tmpl = ScheduleTemplate(name="daily-backup", schedule="0 2 * * *", command_pattern="backup")
        entry = _entry("0 3 * * *", "/usr/bin/backup.sh")
        assert not tmpl.matches(entry)

    def test_no_match_wrong_command(self):
        tmpl = ScheduleTemplate(name="daily-backup", schedule="0 2 * * *", command_pattern="backup")
        entry = _entry("0 2 * * *", "/usr/bin/cleanup.sh")
        assert not tmpl.matches(entry)

    def test_matches_regex_command_pattern(self):
        tmpl = ScheduleTemplate(name="any-backup", schedule="0 2 * * *", command_pattern=r"back.*\.sh")
        entry = _entry("0 2 * * *", "/usr/bin/backup_full.sh")
        assert tmpl.matches(entry)

    def test_matches_wildcard_schedule(self):
        """A template with schedule='*' should match any schedule."""
        tmpl = ScheduleTemplate(name="any-time", schedule="*", command_pattern="sync")
        entry = _entry("*/5 * * * *", "/usr/bin/sync_data")
        assert tmpl.matches(entry)

    def test_case_insensitive_command_match(self):
        tmpl = ScheduleTemplate(name="backup", schedule="0 2 * * *", command_pattern="BACKUP")
        entry = _entry("0 2 * * *", "/usr/bin/backup.sh")
        # default matching should be case-insensitive
        assert tmpl.matches(entry)


# ---------------------------------------------------------------------------
# TemplateReport
# ---------------------------------------------------------------------------

class TestTemplateReport:
    def _make_match(self, template_name: str, host: str, command: str) -> TemplateMatch:
        entry = _entry("0 1 * * *", command, host=host)
        tmpl = ScheduleTemplate(name=template_name, schedule="0 1 * * *", command_pattern=command)
        return TemplateMatch(template=tmpl, entry=entry)

    def test_total_counts_all_matches(self):
        matches = [
            self._make_match("t1", "host1", "cmd_a"),
            self._make_match("t1", "host2", "cmd_a"),
            self._make_match("t2", "host1", "cmd_b"),
        ]
        report = TemplateReport(matches=matches)
        assert report.total == 3

    def test_total_empty(self):
        report = TemplateReport(matches=[])
        assert report.total == 0

    def test_by_template_groups_correctly(self):
        matches = [
            self._make_match("t1", "host1", "cmd_a"),
            self._make_match("t1", "host2", "cmd_a"),
            self._make_match("t2", "host1", "cmd_b"),
        ]
        report = TemplateReport(matches=matches)
        grouped = report.by_template()
        assert "t1" in grouped
        assert "t2" in grouped
        assert len(grouped["t1"]) == 2
        assert len(grouped["t2"]) == 1

    def test_by_template_empty(self):
        report = TemplateReport(matches=[])
        assert report.by_template() == {}

    def test_hosts_returns_unique_hosts(self):
        matches = [
            self._make_match("t1", "host1", "cmd_a"),
            self._make_match("t1", "host1", "cmd_a"),
            self._make_match("t2", "host2", "cmd_b"),
        ]
        report = TemplateReport(matches=matches)
        assert report.hosts() == {"host1", "host2"}


# ---------------------------------------------------------------------------
# diff_entries (template-level diff helper)
# ---------------------------------------------------------------------------

class TestDiffEntries:
    def test_diff_finds_unmatched_entries(self):
        templates = [
            ScheduleTemplate(name="backup", schedule="0 2 * * *", command_pattern="backup"),
        ]
        entries = [
            _entry("0 2 * * *", "/usr/bin/backup.sh"),
            _entry("*/5 * * * *", "/usr/bin/unknown_job.sh"),
        ]
        report = diff_entries(templates, entries)
        assert report.total == 1  # only the backup matched
        unmatched = [e for e in entries if not any(t.matches(e) for t in templates)]
        assert len(unmatched) == 1
        assert "unknown_job" in unmatched[0].command

    def test_diff_all_matched(self):
        templates = [
            ScheduleTemplate(name="backup", schedule="0 2 * * *", command_pattern="backup"),
            ScheduleTemplate(name="sync", schedule="*/5 * * * *", command_pattern="sync"),
        ]
        entries = [
            _entry("0 2 * * *", "/usr/bin/backup.sh"),
            _entry("*/5 * * * *", "/usr/bin/sync_data"),
        ]
        report = diff_entries(templates, entries)
        assert report.total == 2

    def test_diff_no_entries(self):
        templates = [
            ScheduleTemplate(name="backup", schedule="0 2 * * *", command_pattern="backup"),
        ]
        report = diff_entries(templates, [])
        assert report.total == 0
