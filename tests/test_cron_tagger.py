"""Tests for cron_tagger module — filtering and annotating entries by tag."""

import pytest
from unittest.mock import MagicMock

from cronclear.cron_tagger import (
    filter_results_by_tag,
    annotate_entries_with_tags,
    group_results_by_tag,
)
from cronclear.cron_parser import CronEntry, ParseResult
from cronclear.cron_collector import CollectionResult
from cronclear.tag_manager import TagManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(command: str, host: str = "web-01", user: str = "root") -> CronEntry:
    entry = MagicMock(spec=CronEntry)
    entry.command = command
    entry.host = host
    entry.user = user
    entry.raw = f"* * * * * {command}"
    return entry


def _parse_result(host: str, entries: list) -> ParseResult:
    result = MagicMock(spec=ParseResult)
    result.host = host
    result.entries = entries
    result.errors = []
    return result


def _collection_result(host: str, entries: list) -> CollectionResult:
    result = MagicMock(spec=CollectionResult)
    result.host = host
    result.parse_result = _parse_result(host, entries)
    result.error = None
    return result


def _tag_manager(tags_by_host: dict) -> TagManager:
    """Build a TagManager mock that returns tags per host."""
    tm = MagicMock(spec=TagManager)
    tm.tags_for_host.side_effect = lambda host: tags_by_host.get(host, [])
    tm.hosts_with_tag.side_effect = lambda tag: [
        h for h, tags in tags_by_host.items() if tag in tags
    ]
    return tm


# ---------------------------------------------------------------------------
# filter_results_by_tag
# ---------------------------------------------------------------------------

def test_filter_results_keeps_matching_hosts():
    tm = _tag_manager({"web-01": ["web"], "db-01": ["db"]})
    results = [
        _collection_result("web-01", [_entry("/opt/web.sh")]),
        _collection_result("db-01", [_entry("/opt/db.sh")]),
    ]
    filtered = filter_results_by_tag(results, "web", tm)
    assert len(filtered) == 1
    assert filtered[0].host == "web-01"


def test_filter_results_returns_empty_when_no_match():
    tm = _tag_manager({"web-01": ["web"]})
    results = [_collection_result("web-01", [_entry("/opt/web.sh")])]
    filtered = filter_results_by_tag(results, "db", tm)
    assert filtered == []


def test_filter_results_all_match():
    tm = _tag_manager({"web-01": ["prod"], "web-02": ["prod"]})
    results = [
        _collection_result("web-01", []),
        _collection_result("web-02", []),
    ]
    filtered = filter_results_by_tag(results, "prod", tm)
    assert len(filtered) == 2


# ---------------------------------------------------------------------------
# annotate_entries_with_tags
# ---------------------------------------------------------------------------

def test_annotate_entries_attaches_tags():
    tm = _tag_manager({"web-01": ["web", "prod"]})
    entries = [_entry("/opt/web.sh", host="web-01")]
    annotated = annotate_entries_with_tags(entries, tm)
    # Returns list of (entry, tags) tuples
    assert len(annotated) == 1
    entry, tags = annotated[0]
    assert entry.command == "/opt/web.sh"
    assert set(tags) == {"web", "prod"}


def test_annotate_entries_empty_tags_for_unknown_host():
    tm = _tag_manager({})
    entries = [_entry("/opt/script.sh", host="unknown-99")]
    annotated = annotate_entries_with_tags(entries, tm)
    _, tags = annotated[0]
    assert tags == []


def test_annotate_entries_multiple_hosts():
    tm = _tag_manager({"web-01": ["web"], "db-01": ["db"]})
    entries = [
        _entry("/opt/web.sh", host="web-01"),
        _entry("/opt/db.sh", host="db-01"),
    ]
    annotated = annotate_entries_with_tags(entries, tm)
    assert len(annotated) == 2
    tags_map = {e.host: t for e, t in annotated}
    assert tags_map["web-01"] == ["web"]
    assert tags_map["db-01"] == ["db"]


# ---------------------------------------------------------------------------
# group_results_by_tag
# ---------------------------------------------------------------------------

def test_group_results_by_tag_basic():
    tm = _tag_manager({"web-01": ["web", "prod"], "db-01": ["db", "prod"]})
    results = [
        _collection_result("web-01", []),
        _collection_result("db-01", []),
    ]
    grouped = group_results_by_tag(results, tm)
    assert "web" in grouped
    assert "prod" in grouped
    assert "db" in grouped
    assert len(grouped["prod"]) == 2


def test_group_results_by_tag_no_tags():
    tm = _tag_manager({})
    results = [_collection_result("web-01", [])]
    grouped = group_results_by_tag(results, tm)
    assert grouped == {}


def test_group_results_by_tag_single_tag():
    tm = _tag_manager({"web-01": ["staging"]})
    results = [_collection_result("web-01", [])]
    grouped = group_results_by_tag(results, tm)
    assert list(grouped.keys()) == ["staging"]
    assert grouped["staging"][0].host == "web-01"
