"""Filter and group hosts based on tags, patterns, or custom criteria."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable


@dataclass
class HostGroup:
    """A named collection of host addresses."""

    name: str
    hosts: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.hosts)


def filter_by_pattern(hosts: Iterable[str], pattern: str) -> list[str]:
    """Return hosts matching a shell-style glob pattern (e.g. 'web-*.prod')."""
    return [h for h in hosts if fnmatch.fnmatch(h, pattern)]


def filter_by_regex(hosts: Iterable[str], regex: str) -> list[str]:
    """Return hosts matching a regular expression."""
    compiled = re.compile(regex)
    return [h for h in hosts if compiled.search(h)]


def filter_by_predicate(hosts: Iterable[str], predicate: Callable[[str], bool]) -> list[str]:
    """Return hosts for which *predicate* returns True."""
    return [h for h in hosts if predicate(h)]


def group_by_prefix(hosts: Iterable[str], separator: str = "-") -> dict[str, HostGroup]:
    """Group hosts by the first segment of their name split on *separator*.

    Example::

        group_by_prefix(["web-01", "web-02", "db-01"])
        # -> {"web": HostGroup(name="web", hosts=["web-01", "web-02"]),
        #     "db":  HostGroup(name="db",  hosts=["db-01"])}
    """
    groups: dict[str, HostGroup] = {}
    for host in hosts:
        prefix = host.split(separator, maxsplit=1)[0]
        if prefix not in groups:
            groups[prefix] = HostGroup(name=prefix)
        groups[prefix].hosts.append(host)
    return groups


def exclude_hosts(hosts: Iterable[str], excluded: Iterable[str]) -> list[str]:
    """Return *hosts* minus any host listed in *excluded*."""
    excluded_set = set(excluded)
    return [h for h in hosts if h not in excluded_set]
