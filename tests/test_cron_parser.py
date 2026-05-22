"""Tests for cronclear.cron_parser module."""

import pytest
from cronclear.cron_parser import CronEntry, ParseResult, parse_crontab


SAMPLE_CRONTAB = """
# Daily backup
0 2 * * * /usr/local/bin/backup.sh
*/5 * * * * /usr/bin/healthcheck.py --quiet
@reboot /usr/sbin/start_agent.sh
"""


def test_parse_standard_entries():
    result = parse_crontab(SAMPLE_CRONTAB)
    assert len(result.entries) == 3
    assert len(result.errors) == 0


def test_parse_ignores_comments_and_blanks():
    output = "# this is a comment\n\n  \n0 0 * * * /bin/true"
    result = parse_crontab(output)
    assert len(result.entries) == 1


def test_parse_standard_entry_fields():
    result = parse_crontab("0 2 * * * /usr/local/bin/backup.sh")
    entry = result.entries[0]
    assert entry.minute == "0"
    assert entry.hour == "2"
    assert entry.day_of_month == "*"
    assert entry.month == "*"
    assert entry.day_of_week == "*"
    assert entry.command == "/usr/local/bin/backup.sh"


def test_parse_at_shortcut():
    result = parse_crontab("@reboot /usr/sbin/start_agent.sh")
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.minute == "@reboot"
    assert entry.command == "/usr/sbin/start_agent.sh"


def test_parse_attaches_user_and_host():
    result = parse_crontab("0 0 * * * /bin/true", user="alice", host="web01")
    entry = result.entries[0]
    assert entry.user == "alice"
    assert entry.host == "web01"


def test_parse_records_error_for_malformed_line():
    result = parse_crontab("not-enough-fields")
    assert len(result.entries) == 0
    assert len(result.errors) == 1
    assert "could not parse" in result.errors[0]


def test_parse_records_error_for_bare_at_shortcut():
    result = parse_crontab("@reboot")
    assert len(result.entries) == 0
    assert "malformed shortcut" in result.errors[0]


def test_entry_schedule_property():
    entry = CronEntry(
        minute="0", hour="3", day_of_month="*",
        month="*", day_of_week="1",
        command="/bin/weekly", raw_line="0 3 * * 1 /bin/weekly"
    )
    assert entry.schedule == "0 3 * * 1"


def test_entry_str_includes_host_and_user():
    entry = CronEntry(
        minute="0", hour="1", day_of_month="*",
        month="*", day_of_week="*",
        command="/bin/cmd", raw_line="0 1 * * * /bin/cmd",
        user="bob", host="db02",
    )
    text = str(entry)
    assert "bob@db02" in text
    assert "/bin/cmd" in text


def test_parse_result_stores_raw_output():
    raw = "0 0 * * * /bin/true"
    result = parse_crontab(raw)
    assert result.raw_output == raw
