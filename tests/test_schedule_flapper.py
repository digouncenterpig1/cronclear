"""Tests for cronclear.schedule_flapper."""
from __future__ import annotations

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.schedule_flapper import FlapEntry, detect_flapping
from cronclear.schedule_watcher import Snapshot


def _entry(raw: str, host: str = "host1") -> CronEntry:
    e = CronEntry.__new__(CronEntry)
    e.minute = "*"
    e.hour = "*"
    e.dom = "*"
    e.month = "*"
    e.dow = "*"
    e.command = raw
    e.user = "root"
    e.host = host
    return e


def _snap(host_entries: dict) -> Snapshot:
    return Snapshot(entries=host_entries)


# ---------------------------------------------------------------------------
# FlapEntry helpers
# ---------------------------------------------------------------------------

def test_flap_ratio_fully_present():
    fe = FlapEntry(host="h", raw="cmd", present_in=["s1", "s2"], absent_in=[])
    assert fe.flap_ratio == 0.0
    assert not fe.is_flapping


def test_flap_ratio_fully_absent():
    fe = FlapEntry(host="h", raw="cmd", present_in=[], absent_in=["s1", "s2"])
    assert fe.flap_ratio == 1.0
    assert not fe.is_flapping


def test_flap_ratio_partial():
    fe = FlapEntry(host="h", raw="cmd", present_in=["s1"], absent_in=["s2"])
    assert fe.flap_ratio == pytest.approx(0.5)
    assert fe.is_flapping


# ---------------------------------------------------------------------------
# detect_flapping
# ---------------------------------------------------------------------------

def test_no_snapshots_returns_empty_report():
    report = detect_flapping([])
    assert not report.has_flappers
    assert report.entries == []


def test_single_snapshot_no_flappers():
    e = _entry("/usr/bin/backup")
    snap = _snap({"host1": [e]})
    report = detect_flapping([snap])
    assert not report.has_flappers


def test_stable_entry_not_flapping():
    e = _entry("/usr/bin/backup")
    s1 = _snap({"host1": [e]})
    s2 = _snap({"host1": [e]})
    report = detect_flapping([s1, s2])
    assert not report.has_flappers


def test_entry_present_then_absent_is_flapping():
    e = _entry("/usr/bin/cleanup")
    s1 = _snap({"host1": [e]})
    s2 = _snap({"host1": []})
    report = detect_flapping([s1, s2], labels=["snap-a", "snap-b"])
    assert report.has_flappers
    flapper = report.flapping[0]
    assert flapper.host == "host1"
    assert "snap-a" in flapper.present_in
    assert "snap-b" in flapper.absent_in


def test_entry_absent_then_present_is_flapping():
    e = _entry("/opt/run.sh")
    s1 = _snap({"host2": []})
    s2 = _snap({"host2": [e]})
    report = detect_flapping([s1, s2])
    assert report.has_flappers


def test_labels_length_mismatch_raises():
    s = _snap({})
    with pytest.raises(ValueError):
        detect_flapping([s, s], labels=["only-one"])


def test_multiple_hosts_independent():
    e1 = _entry("/bin/a", host="h1")
    e2 = _entry("/bin/b", host="h2")
    s1 = _snap({"h1": [e1], "h2": [e2]})
    s2 = _snap({"h1": [],    "h2": [e2]})
    report = detect_flapping([s1, s2])
    flappers = report.flapping
    assert len(flappers) == 1
    assert flappers[0].host == "h1"
