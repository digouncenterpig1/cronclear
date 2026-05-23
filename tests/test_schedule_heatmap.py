"""Tests for schedule_heatmap module."""

import pytest
from cronclear.cron_parser import CronEntry
from cronclear.schedule_heatmap import (
    HeatmapData,
    DAYS,
    build_heatmap,
    _expand_field,
)


def _entry(schedule: str, command: str = "cmd") -> CronEntry:
    return CronEntry(
        schedule=schedule,
        command=command,
        user="root",
        host="host1",
        raw=f"{schedule} {command}",
    )


# --- _expand_field ---

def test_expand_star():
    assert _expand_field("*", 0, 6) == list(range(7))


def test_expand_single_value():
    assert _expand_field("3", 0, 23) == [3]


def test_expand_range():
    assert _expand_field("1-3", 0, 23) == [1, 2, 3]


def test_expand_step():
    assert _expand_field("*/6", 0, 23) == [0, 6, 12, 18]


def test_expand_list():
    assert _expand_field("1,3,5", 0, 23) == [1, 3, 5]


# --- build_heatmap ---

def test_build_heatmap_empty():
    hm = build_heatmap([])
    assert hm.total_hits() == 0


def test_build_heatmap_single_entry():
    # fires every day at hour 2
    e = _entry("0 2 * * *")
    hm = build_heatmap([e])
    for d in range(7):
        assert hm.counts[d][2] == 1
    assert hm.counts[0][3] == 0


def test_build_heatmap_skips_shortcuts():
    e = _entry("@daily")
    hm = build_heatmap([e])
    assert hm.total_hits() == 0


def test_build_heatmap_multiple_entries_accumulate():
    entries = [
        _entry("0 3 * * 1"),  # Monday hour 3
        _entry("0 3 * * 1"),  # same slot again
    ]
    hm = build_heatmap(entries)
    assert hm.counts[1][3] == 2  # day index 1 = Monday


def test_build_heatmap_step_hours():
    # every 6 hours, every day
    e = _entry("0 */6 * * *")
    hm = build_heatmap([e])
    for d in range(7):
        for h in [0, 6, 12, 18]:
            assert hm.counts[d][h] == 1
        assert hm.counts[d][1] == 0


# --- HeatmapData helpers ---

def test_busiest_hour():
    entries = [_entry("0 4 * * *"), _entry("30 4 * * *")]
    hm = build_heatmap(entries)
    assert hm.busiest_hour() == 4


def test_busiest_day():
    # only fires on Wednesday (index 3)
    e = _entry("0 10 * * 3")
    hm = build_heatmap([e])
    assert hm.busiest_day() == "Wed"


def test_total_hits_counts_all_slots():
    # 1 entry, fires every hour every day = 24*7 hits
    e = _entry("0 * * * *")
    hm = build_heatmap([e])
    assert hm.total_hits() == 24 * 7
