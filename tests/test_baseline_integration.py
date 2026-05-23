"""Integration-style tests: save then compare using real files."""
import json
from pathlib import Path

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.schedule_baseline import (
    compare_to_baseline,
    load_baseline,
    save_baseline,
)


def _e(raw: str, user: str = "deploy", host: str = "srv1") -> CronEntry:
    return CronEntry(raw=raw, user=user, host=host)


def test_full_roundtrip_no_changes(tmp_path):
    p = tmp_path / "bl.json"
    entries = [_e("0 2 * * * /opt/backup"), _e("*/10 * * * * healthcheck")]
    save_baseline(entries, p)
    baseline = load_baseline(p)
    report = compare_to_baseline(entries, baseline)
    assert not report.has_changes
    assert report.summary_line() == "No changes from baseline."


def test_full_roundtrip_entry_added(tmp_path):
    p = tmp_path / "bl.json"
    original = [_e("0 2 * * * /opt/backup")]
    save_baseline(original, p)
    baseline = load_baseline(p)
    updated = original + [_e("5 5 * * * new_job")]
    report = compare_to_baseline(updated, baseline)
    assert report.has_changes
    assert len(report.added) == 1
    assert report.added[0].raw == "5 5 * * * new_job"
    assert not report.removed


def test_full_roundtrip_entry_removed(tmp_path):
    p = tmp_path / "bl.json"
    original = [_e("0 2 * * * /opt/backup"), _e("30 6 * * 1 weekly")]
    save_baseline(original, p)
    baseline = load_baseline(p)
    report = compare_to_baseline([_e("0 2 * * * /opt/backup")], baseline)
    assert len(report.removed) == 1
    assert report.removed[0].raw == "30 6 * * 1 weekly"


def test_baseline_file_structure(tmp_path):
    p = tmp_path / "bl.json"
    save_baseline([_e("* * * * * ping", user="ops", host="db1")], p)
    raw = json.loads(p.read_text())
    assert raw[0] == {"raw": "* * * * * ping", "user": "ops", "host": "db1"}


def test_empty_baseline_all_added(tmp_path):
    p = tmp_path / "bl.json"
    save_baseline([], p)
    baseline = load_baseline(p)
    entries = [_e("0 0 * * * nightly")]
    report = compare_to_baseline(entries, baseline)
    assert len(report.added) == 1
    assert not report.removed
