"""Integration tests: search through realistic CollectionResult data."""
from __future__ import annotations

from cronclear.cron_parser import ParseResult
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_search import search_entries


class _E:
    """Minimal cron entry stub."""
    def __init__(self, cmd, sched="0 2 * * *", user="root"):
        self.command = cmd
        self.user = user
        self._sched = sched

    @property
    def schedule(self):
        class _S:
            def __init__(s, v): s._v = v
            def __str__(s): return s._v
        return _S(self._sched)


def _cr(host, entries):
    return CollectionResult(host=host, parse_result=ParseResult(entries=entries, errors=[]), error=None)


def test_search_across_three_hosts():
    hosts = [
        _cr("web-01", [_E("/usr/bin/certbot renew"), _E("/bin/backup")]),
        _cr("web-02", [_E("/usr/bin/certbot renew"), _E("/bin/logrotate")]),
        _cr("db-01",  [_E("/bin/pg_dump"), _E("/bin/backup")]),
    ]
    report = search_entries(hosts, "backup")
    assert report.total == 2
    assert sorted(report.hosts) == ["db-01", "web-01"]


def test_search_command_field_only():
    hosts = [
        _cr("h1", [_E("/bin/backup", user="backup")]),
    ]
    # Without field restriction both command and user would match
    report_any = search_entries(hosts, "backup")
    assert report_any.total == 1
    assert report_any.results[0].matched_field == "command"  # command checked first

    report_user = search_entries(hosts, "backup", field="user")
    assert report_user.total == 1
    assert report_user.results[0].matched_field == "user"


def test_search_schedule_field():
    hosts = [
        _cr("h1", [_E("/bin/foo", sched="*/5 * * * *"), _E("/bin/bar", sched="0 1 * * *")]),
    ]
    report = search_entries(hosts, r"\*/5", field="schedule")
    assert report.total == 1
    assert report.results[0].entry.command == "/bin/foo"


def test_search_empty_collection():
    report = search_entries([], "anything")
    assert report.total == 0
    assert report.hosts == []


def test_search_returns_correct_host_per_entry():
    hosts = [
        _cr("alpha", [_E("/bin/sync")]),
        _cr("beta",  [_E("/bin/sync")]),
        _cr("gamma", [_E("/bin/other")]),
    ]
    report = search_entries(hosts, "sync")
    found_hosts = {r.host for r in report.results}
    assert found_hosts == {"alpha", "beta"}
