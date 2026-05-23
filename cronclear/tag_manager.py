"""Tag manager: attach and query user-defined tags on hosts and cron entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


# tag store: {host -> [tag, ...]}
_TagStore = Dict[str, List[str]]


class TagManager:
    """Load, persist, and query host/entry tags."""

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self._path = store_path
        self._store: _TagStore = {}
        if store_path and store_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            self._store = json.load(fh)

    def save(self) -> None:
        if self._path is None:
            raise ValueError("No store_path configured for TagManager")
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._store, fh, indent=2)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_tag(self, host: str, tag: str) -> None:
        """Add *tag* to *host*; silently ignores duplicates."""
        tags = self._store.setdefault(host, [])
        if tag not in tags:
            tags.append(tag)

    def remove_tag(self, host: str, tag: str) -> bool:
        """Remove *tag* from *host*. Returns True if the tag existed."""
        tags = self._store.get(host, [])
        if tag in tags:
            tags.remove(tag)
            return True
        return False

    def clear_host(self, host: str) -> None:
        """Remove all tags for *host*."""
        self._store.pop(host, None)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def tags_for(self, host: str) -> List[str]:
        return list(self._store.get(host, []))

    def hosts_with_tag(self, tag: str) -> List[str]:
        return [h for h, tags in self._store.items() if tag in tags]

    def all_tags(self) -> List[str]:
        seen: List[str] = []
        for tags in self._store.values():
            for t in tags:
                if t not in seen:
                    seen.append(t)
        return seen

    def filter_hosts(self, hosts: List[str], tag: str) -> List[str]:
        """Return only those *hosts* that carry *tag*."""
        tagged = set(self.hosts_with_tag(tag))
        return [h for h in hosts if h in tagged]
