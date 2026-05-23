"""Tests for schedule_grouper module."""
from __future__ import annotations

import pytest

from cronclear.cron_parser import CronEntry
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_grouper import (
    ScheduleGroup,
    group_by_schedule,
    group_by_command_prefix,
    unique_schedules,
)


def _entry(schedule: str, command: str, host: str = "host1") -> CronEntry:
    return CronEntry(
        minute=schedule.split()[0],
        hour=schedule.split()[1],
        dom=schedule.split()[2],
        month=schedule.split()[3],
        dow=schedule.split()[4],
        command=command,
        user="root",
        host=host,
        raw=f"{schedule} root {command}",
    )


def _result(host: str, entries) -> CollectionResult:
    return CollectionResult(host=host, entries=entries, errors=[])


def test_group_by_schedule_single_group():
    e1 = _entry("0 2 * * *", "/usr/bin/backup")
    e2 = _entry("0 2 * * *", "/usr/bin/cleanup", host="host2")
    result = group_by_schedule([_result("host1", [e1]), _result("host2", [e2])])
    assert "0 2 * * *" in result
    grp = result["0 2 * * *"]
    assert grp.command_count == 2
    assert grp.host_count == 2


def test_group_by_schedule_multiple_groups():
    e1 = _entry("0 2 * * *", "/usr/bin/backup")
    e2 = _entry("*/5 * * * *", "/usr/bin/heartbeat")
    result = group_by_schedule([_result("host1", [e1, e2])])
    assert len(result) == 2


def test_group_by_schedule_empty():
    assert group_by_schedule([]) == {}


def test_schedule_group_host_count_deduplicates():
    e1 = _entry("0 1 * * *", "/a", host="web1")
    e2 = _entry("0 1 * * *", "/b", host="web1")
    grp = ScheduleGroup(schedule="0 1 * * *", entries=[e1, e2])
    assert grp.host_count == 1


def test_group_by_command_prefix_depth1():
    e1 = _entry("0 * * * *", "/usr/bin/foo")
    e2 = _entry("0 * * * *", "/usr/bin/bar")
    e3 = _entry("0 * * * *", "/opt/scripts/run")
    groups = group_by_command_prefix([_result("h", [e1, e2, e3])], depth=1)
    assert "/usr" in groups
    assert "/opt" in groups
    assert len(groups["/usr"]) == 2


def test_group_by_command_prefix_depth2():
    e1 = _entry("0 * * * *", "/usr/bin/foo")
    e2 = _entry("0 * * * *", "/usr/local/bar")
    groups = group_by_command_prefix([_result("h", [e1, e2])], depth=2)
    assert "/usr/bin" in groups
    assert "/usr/local" in groups


def test_unique_schedules_sorted():
    e1 = _entry("0 2 * * *", "/a")
    e2 = _entry("*/5 * * * *", "/b")
    e3 = _entry("0 2 * * *", "/c")
    schedules = unique_schedules([_result("h", [e1, e2, e3])])
    assert schedules == sorted({"0 2 * * *", "*/5 * * * *"})
    assert len(schedules) == 2


def test_unique_schedules_empty():
    assert unique_schedules([]) == []
