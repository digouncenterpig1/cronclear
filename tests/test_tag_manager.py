"""Tests for cronclear.tag_manager."""

import json
import pytest
from pathlib import Path

from cronclear.tag_manager import TagManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manager() -> TagManager:
    """Fresh in-memory TagManager."""
    return TagManager(store_path=None)


# ---------------------------------------------------------------------------
# add / query
# ---------------------------------------------------------------------------


def test_add_tag_and_retrieve():
    tm = _manager()
    tm.add_tag("web01", "production")
    assert "production" in tm.tags_for("web01")


def test_add_tag_no_duplicates():
    tm = _manager()
    tm.add_tag("web01", "production")
    tm.add_tag("web01", "production")
    assert tm.tags_for("web01").count("production") == 1


def test_tags_for_unknown_host_returns_empty():
    tm = _manager()
    assert tm.tags_for("ghost") == []


def test_hosts_with_tag():
    tm = _manager()
    tm.add_tag("web01", "production")
    tm.add_tag("web02", "production")
    tm.add_tag("db01", "staging")
    assert set(tm.hosts_with_tag("production")) == {"web01", "web02"}


def test_hosts_with_tag_none():
    tm = _manager()
    assert tm.hosts_with_tag("nope") == []


def test_all_tags_unique():
    tm = _manager()
    tm.add_tag("web01", "production")
    tm.add_tag("web02", "production")
    tm.add_tag("db01", "staging")
    assert set(tm.all_tags()) == {"production", "staging"}


# ---------------------------------------------------------------------------
# remove / clear
# ---------------------------------------------------------------------------


def test_remove_tag_returns_true():
    tm = _manager()
    tm.add_tag("web01", "production")
    assert tm.remove_tag("web01", "production") is True
    assert "production" not in tm.tags_for("web01")


def test_remove_tag_missing_returns_false():
    tm = _manager()
    assert tm.remove_tag("web01", "ghost") is False


def test_clear_host():
    tm = _manager()
    tm.add_tag("web01", "production")
    tm.add_tag("web01", "critical")
    tm.clear_host("web01")
    assert tm.tags_for("web01") == []


# ---------------------------------------------------------------------------
# filter_hosts
# ---------------------------------------------------------------------------


def test_filter_hosts_keeps_tagged():
    tm = _manager()
    tm.add_tag("web01", "production")
    tm.add_tag("db01", "production")
    result = tm.filter_hosts(["web01", "db01", "ci01"], "production")
    assert set(result) == {"web01", "db01"}


def test_filter_hosts_empty_when_no_match():
    tm = _manager()
    result = tm.filter_hosts(["web01", "web02"], "production")
    assert result == []


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def test_save_and_load(tmp_path: Path):
    store = tmp_path / "tags.json"
    tm = TagManager(store_path=store)
    tm.add_tag("web01", "production")
    tm.add_tag("db01", "staging")
    tm.save()

    tm2 = TagManager(store_path=store)
    assert "production" in tm2.tags_for("web01")
    assert "staging" in tm2.tags_for("db01")


def test_save_without_path_raises():
    tm = _manager()
    with pytest.raises(ValueError, match="No store_path"):
        tm.save()
