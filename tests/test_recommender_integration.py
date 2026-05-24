"""Integration tests: recommender + collector + scorer pipeline."""
from __future__ import annotations
from cronclear.cron_parser import CronEntry, parse_crontab
from cronclear.cron_collector import CollectionResult
from cronclear.schedule_recommender import recommend


RAW_CRONTAB = """
# system crontab
* * * * * root /usr/bin/poll_service
0 3 * * * root /usr/bin/nightly_backup
*/2 * * * * root /usr/bin/frequent_check
@daily root /usr/bin/daily_cleanup
"""


def _build_result(host: str, raw: str) -> CollectionResult:
    parse = parse_crontab(raw, host=host)
    return CollectionResult(host=host, entries=parse.entries)


def test_pipeline_produces_recommendations():
    result = _build_result("app1", RAW_CRONTAB)
    report = recommend(result.entries)
    assert report.total >= 1


def test_pipeline_skips_daily_shortcut():
    result = _build_result("app1", RAW_CRONTAB)
    report = recommend(result.entries)
    commands = [r.command for r in report.recommendations]
    assert "/usr/bin/daily_cleanup" not in commands


def test_pipeline_flags_every_minute():
    result = _build_result("app1", RAW_CRONTAB)
    report = recommend(result.entries)
    commands = [r.command for r in report.recommendations]
    assert "/usr/bin/poll_service" in commands


def test_pipeline_nightly_backup_clean():
    result = _build_result("app1", RAW_CRONTAB)
    report = recommend(result.entries)
    commands = [r.command for r in report.recommendations]
    assert "/usr/bin/nightly_backup" not in commands


def test_multi_host_recommendations():
    r1 = _build_result("web1", "* * * * * root /usr/bin/poll\n")
    r2 = _build_result("web2", "0 4 * * * root /usr/bin/backup\n")
    all_entries = r1.entries + r2.entries
    report = recommend(all_entries)
    hosts = {rec.host for rec in report.recommendations}
    assert "web1" in hosts
    assert "web2" not in hosts
