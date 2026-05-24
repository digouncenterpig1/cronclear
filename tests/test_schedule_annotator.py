import pytest
from unittest.mock import MagicMock
from cronclear.schedule_annotator import (
    annotate_entries,
    AnnotationReport,
    AnnotatedEntry,
    _resolve_label,
)


def _entry(schedule: str, command: str = "/usr/bin/cmd") -> MagicMock:
    e = MagicMock()
    e.schedule = schedule
    e.command = command
    e.is_shortcut = schedule.startswith("@")
    return e


# --- _resolve_label ---

def test_label_reboot():
    assert _resolve_label(_entry("@reboot")) == "on reboot"


def test_label_hourly_shortcut():
    assert _resolve_label(_entry("@hourly")) == "hourly"


def test_label_hourly_explicit():
    assert _resolve_label(_entry("0 * * * *")) == "hourly"


def test_label_daily_shortcut():
    assert _resolve_label(_entry("@daily")) == "daily"


def test_label_daily_explicit():
    assert _resolve_label(_entry("0 0 * * *")) == "daily"


def test_label_weekly():
    assert _resolve_label(_entry("@weekly")) == "weekly"


def test_label_monthly():
    assert _resolve_label(_entry("@monthly")) == "monthly"


def test_label_yearly():
    assert _resolve_label(_entry("@yearly")) == "yearly"


def test_label_every_minute():
    e = _entry("* * * * *")
    e.is_shortcut = False
    assert _resolve_label(e) == "every minute"


def test_label_every_n_minutes():
    e = _entry("*/5 * * * *")
    e.is_shortcut = False
    assert _resolve_label(e) == "every N minutes"


def test_label_every_n_hours():
    e = _entry("0 */4 * * *")
    e.is_shortcut = False
    assert _resolve_label(e) == "every N hours"


def test_label_custom_fallback():
    e = _entry("30 2 15 * *")
    e.is_shortcut = False
    assert _resolve_label(e) == "custom"


# --- annotate_entries ---

def test_annotate_returns_report():
    entries = [_entry("@daily"), _entry("@hourly")]
    report = annotate_entries(entries)
    assert isinstance(report, AnnotationReport)
    assert report.total == 2


def test_annotate_labels_match():
    entries = [_entry("@daily"), _entry("@reboot")]
    report = annotate_entries(entries)
    labels = [a.label for a in report.entries]
    assert "daily" in labels
    assert "on reboot" in labels


def test_annotate_by_label_filter():
    entries = [_entry("@daily"), _entry("@hourly"), _entry("@daily")]
    report = annotate_entries(entries)
    daily = report.by_label("daily")
    assert len(daily) == 2


def test_annotate_note_attached():
    entries = [_entry("@daily", command="/opt/backup.sh")]
    report = annotate_entries(entries, notes={"backup": "nightly backup job"})
    assert report.entries[0].note == "nightly backup job"


def test_annotate_note_not_matched():
    entries = [_entry("@daily", command="/usr/bin/other")]
    report = annotate_entries(entries, notes={"backup": "nightly backup job"})
    assert report.entries[0].note is None


def test_annotate_empty_list():
    report = annotate_entries([])
    assert report.total == 0
    assert report.by_label("daily") == []
