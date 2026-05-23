"""Helpers to tag-filter CronEntry / CollectionResult objects."""

from __future__ import annotations

from typing import List

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult
from cronclear.tag_manager import TagManager


def filter_results_by_tag(
    results: List[CollectionResult],
    tag: str,
    manager: TagManager,
) -> List[CollectionResult]:
    """Return only those CollectionResults whose host carries *tag*."""
    tagged = set(manager.hosts_with_tag(tag))
    return [r for r in results if r.host in tagged]


def annotate_entries_with_tags(
    entries: List[CronEntry],
    manager: TagManager,
) -> List[dict]:
    """Return a list of dicts enriching each CronEntry with its host tags."""
    out = []
    for entry in entries:
        tags = manager.tags_for(entry.host) if entry.host else []
        out.append(
            {
                "host": entry.host,
                "user": entry.user,
                "schedule": str(entry.schedule),
                "command": entry.command,
                "tags": tags,
            }
        )
    return out


def group_results_by_tag(
    results: List[CollectionResult],
    manager: TagManager,
) -> dict:
    """Group CollectionResults by their tags.

    Returns {tag: [CollectionResult, ...]}.
    Hosts with multiple tags appear under each tag.
    Hosts with no tags appear under the empty-string key.
    """
    grouped: dict = {}
    for result in results:
        tags = manager.tags_for(result.host)
        if not tags:
            grouped.setdefault("", []).append(result)
        for tag in tags:
            grouped.setdefault(tag, []).append(result)
    return grouped
