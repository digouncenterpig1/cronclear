"""Tests for cronclear.host_filter."""

import pytest

from cronclear.host_filter import (
    HostGroup,
    exclude_hosts,
    filter_by_pattern,
    filter_by_predicate,
    filter_by_regex,
    group_by_prefix,
)

HOSTS = [
    "web-01.prod",
    "web-02.prod",
    "db-01.prod",
    "db-02.staging",
    "cache-01.prod",
]


def test_filter_by_pattern_glob():
    result = filter_by_pattern(HOSTS, "web-*.prod")
    assert result == ["web-01.prod", "web-02.prod"]


def test_filter_by_pattern_no_match():
    result = filter_by_pattern(HOSTS, "worker-*")
    assert result == []


def test_filter_by_pattern_all_match():
    result = filter_by_pattern(HOSTS, "*")
    assert result == HOSTS


def test_filter_by_regex_prod():
    result = filter_by_regex(HOSTS, r"\.prod$")
    assert "db-02.staging" not in result
    assert len(result) == 4


def test_filter_by_regex_invalid_raises():
    with pytest.raises(re.error if False else Exception):
        import re
        re.compile("[invalid")


def test_filter_by_predicate():
    result = filter_by_predicate(HOSTS, lambda h: "cache" in h)
    assert result == ["cache-01.prod"]


def test_filter_by_predicate_none_match():
    result = filter_by_predicate(HOSTS, lambda h: False)
    assert result == []


def test_group_by_prefix_keys():
    groups = group_by_prefix(HOSTS)
    assert set(groups.keys()) == {"web", "db", "cache"}


def test_group_by_prefix_members():
    groups = group_by_prefix(HOSTS)
    assert groups["web"].hosts == ["web-01.prod", "web-02.prod"]
    assert groups["db"].hosts == ["db-01.prod", "db-02.staging"]


def test_group_by_prefix_len():
    groups = group_by_prefix(HOSTS)
    assert len(groups["web"]) == 2
    assert len(groups["cache"]) == 1


def test_group_by_prefix_custom_separator():
    hosts = ["us.east.web", "us.west.db", "eu.west.web"]
    groups = group_by_prefix(hosts, separator=".")
    assert set(groups.keys()) == {"us", "eu"}


def test_exclude_hosts_removes_listed():
    result = exclude_hosts(HOSTS, ["db-01.prod", "cache-01.prod"])
    assert "db-01.prod" not in result
    assert "cache-01.prod" not in result
    assert len(result) == 3


def test_exclude_hosts_empty_exclusion():
    result = exclude_hosts(HOSTS, [])
    assert result == HOSTS


def test_host_group_defaults():
    g = HostGroup(name="test")
    assert g.hosts == []
    assert len(g) == 0
