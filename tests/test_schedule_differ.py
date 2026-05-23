"""Tests for cronclear.schedule_differ."""

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.schedule_differ import DiffResult, diff_entries


def _entry(command: str, schedule: str = "* * * * *", host: str = "h1", user: str = "root") -> CronEntry:
    e = CronEntry(schedule=schedule, command=command)
    e.host = host
    e.user = user
    return e


# ---------------------------------------------------------------------------
# DiffResult helpers
# ---------------------------------------------------------------------------

def test_diff_result_has_changes_true():
    dr = DiffResult(added=[_entry("cmd")], removed=[], unchanged=[])
    assert dr.has_changes is True


def test_diff_result_has_changes_false():
    dr = DiffResult(added=[], removed=[], unchanged=[_entry("cmd")])
    assert dr.has_changes is False


def test_diff_result_summary_line():
    dr = DiffResult(added=[_entry("a")], removed=[_entry("b")], unchanged=[_entry("c"), _entry("d")])
    assert dr.summary_line == "+1 added, -1 removed, 2 unchanged"


# ---------------------------------------------------------------------------
# diff_entries
# ---------------------------------------------------------------------------

def test_diff_no_changes():
    entries = [_entry("backup.sh"), _entry("cleanup.sh")]
    result = diff_entries(entries, entries)
    assert not result.has_changes
    assert len(result.unchanged) == 2


def test_diff_detects_added():
    before = [_entry("backup.sh")]
    after = [_entry("backup.sh"), _entry("new_job.sh")]
    result = diff_entries(before, after)
    assert len(result.added) == 1
    assert result.added[0].command == "new_job.sh"
    assert result.removed == []


def test_diff_detects_removed():
    before = [_entry("backup.sh"), _entry("old_job.sh")]
    after = [_entry("backup.sh")]
    result = diff_entries(before, after)
    assert len(result.removed) == 1
    assert result.removed[0].command == "old_job.sh"
    assert result.added == []


def test_diff_schedule_change_counts_as_remove_and_add():
    before = [_entry("backup.sh", schedule="0 2 * * *")]
    after = [_entry("backup.sh", schedule="0 3 * * *")]
    result = diff_entries(before, after)
    assert len(result.added) == 1
    assert len(result.removed) == 1
    assert result.added[0].schedule == "0 3 * * *"
    assert result.removed[0].schedule == "0 2 * * *"


def test_diff_empty_before():
    after = [_entry("job1.sh"), _entry("job2.sh")]
    result = diff_entries([], after)
    assert len(result.added) == 2
    assert result.removed == []
    assert result.unchanged == []


def test_diff_empty_after():
    before = [_entry("job1.sh")]
    result = diff_entries(before, [])
    assert len(result.removed) == 1
    assert result.added == []


def test_diff_host_distinguishes_entries():
    """Same command on different hosts should be treated as distinct entries."""
    before = [_entry("backup.sh", host="h1")]
    after = [_entry("backup.sh", host="h2")]
    result = diff_entries(before, after)
    assert len(result.added) == 1
    assert len(result.removed) == 1
