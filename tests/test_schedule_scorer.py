"""Tests for cronclear.schedule_scorer."""
from __future__ import annotations

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.schedule_scorer import (
    ScoredEntry,
    score_entries,
    score_entry,
)


def _entry(
    schedule: str = "0 2 * * *",
    command: str = "/usr/bin/backup",
    user: str = "deploy",
    host: str = "web-01",
) -> CronEntry:
    return CronEntry(schedule=schedule, command=command, user=user, host=host)


# ---------------------------------------------------------------------------
# ScoredEntry.risk_label
# ---------------------------------------------------------------------------

def test_risk_label_high():
    e = _entry()
    se = ScoredEntry(entry=e, score=75.0)
    assert se.risk_label == "high"


def test_risk_label_medium():
    e = _entry()
    se = ScoredEntry(entry=e, score=50.0)
    assert se.risk_label == "medium"


def test_risk_label_low():
    e = _entry()
    se = ScoredEntry(entry=e, score=20.0)
    assert se.risk_label == "low"


# ---------------------------------------------------------------------------
# score_entry
# ---------------------------------------------------------------------------

def test_score_every_minute_is_high():
    e = _entry(schedule="* * * * *")
    se = score_entry(e)
    assert se.score >= 40
    assert any("every minute" in r for r in se.reasons)


def test_score_root_user_increases_score():
    e_root = _entry(schedule="0 6 * * *", user="root")
    e_user = _entry(schedule="0 6 * * *", user="deploy")
    assert score_entry(e_root).score > score_entry(e_user).score


def test_score_odd_hour_increases_score():
    e_odd = _entry(schedule="0 3 * * *")   # 3 AM
    e_day = _entry(schedule="0 10 * * *")  # 10 AM
    assert score_entry(e_odd).score > score_entry(e_day).score


def test_score_odd_hour_reason_present():
    e = _entry(schedule="0 1 * * *")
    se = score_entry(e)
    assert any("odd hour" in r for r in se.reasons)


def test_score_shortcut_entry():
    e = CronEntry(schedule="@reboot", command="/start.sh", user="root", host="srv")
    se = score_entry(e)
    assert se.score > 0
    assert any("shortcut" in r for r in se.reasons)


def test_score_frequent_interval():
    e = _entry(schedule="*/2 * * * *")
    se = score_entry(e)
    assert any("2 minute" in r for r in se.reasons)


def test_score_normal_daytime_non_root_is_low():
    e = _entry(schedule="30 9 * * 1-5", user="appuser")
    se = score_entry(e)
    assert se.risk_label == "low"


# ---------------------------------------------------------------------------
# score_entries
# ---------------------------------------------------------------------------

def test_score_entries_sorted_descending():
    entries = [
        _entry(schedule="30 9 * * 1-5", user="deploy"),   # low
        _entry(schedule="* * * * *", user="root"),          # high
        _entry(schedule="0 2 * * *", user="root"),          # medium-ish
    ]
    scored = score_entries(entries)
    scores = [s.score for s in scored]
    assert scores == sorted(scores, reverse=True)


def test_score_entries_empty():
    assert score_entries([]) == []


def test_score_entries_returns_scored_entry_instances():
    entries = [_entry(), _entry(user="root")]
    scored = score_entries(entries)
    assert all(isinstance(s, ScoredEntry) for s in scored)
