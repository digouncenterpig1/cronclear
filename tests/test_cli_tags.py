"""Tests for cronclear.cli_tags sub-commands."""

import argparse
import json
from pathlib import Path

import pytest

from cronclear.cli_tags import build_tag_parser, run_tag_command


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse(args_list, store: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd")
    build_tag_parser(subs)
    ns = parser.parse_args(args_list)
    ns.store = str(store)
    return ns


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


def test_add_creates_tag(tmp_path, capsys):
    store = tmp_path / "tags.json"
    ns = _parse(["tags", "add", "web01", "production"], store)
    rc = run_tag_command(ns)
    assert rc == 0
    data = json.loads(store.read_text())
    assert "production" in data["web01"]
    out = capsys.readouterr().out
    assert "web01" in out


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


def test_remove_existing_tag(tmp_path, capsys):
    store = tmp_path / "tags.json"
    store.write_text(json.dumps({"web01": ["production"]}))
    ns = _parse(["tags", "remove", "web01", "production"], store)
    rc = run_tag_command(ns)
    assert rc == 0
    data = json.loads(store.read_text())
    assert "production" not in data.get("web01", [])


def test_remove_missing_tag_returns_1(tmp_path):
    store = tmp_path / "tags.json"
    store.write_text(json.dumps({}))
    ns = _parse(["tags", "remove", "web01", "ghost"], store)
    rc = run_tag_command(ns)
    assert rc == 1


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_single_host(tmp_path, capsys):
    store = tmp_path / "tags.json"
    store.write_text(json.dumps({"web01": ["production", "critical"]}))
    ns = _parse(["tags", "list", "web01"], store)
    run_tag_command(ns)
    out = capsys.readouterr().out
    assert "production" in out
    assert "critical" in out


def test_list_all_tags(tmp_path, capsys):
    store = tmp_path / "tags.json"
    store.write_text(json.dumps({"web01": ["production"], "db01": ["staging"]}))
    ns = _parse(["tags", "list"], store)
    run_tag_command(ns)
    out = capsys.readouterr().out
    assert "production" in out
    assert "staging" in out


def test_list_host_no_tags(tmp_path, capsys):
    store = tmp_path / "tags.json"
    store.write_text(json.dumps({}))
    ns = _parse(["tags", "list", "web01"], store)
    run_tag_command(ns)
    out = capsys.readouterr().out
    assert "(none)" in out


# ---------------------------------------------------------------------------
# filter
# ---------------------------------------------------------------------------


def test_filter_prints_matching_hosts(tmp_path, capsys):
    store = tmp_path / "tags.json"
    store.write_text(json.dumps({"web01": ["production"], "ci01": ["staging"]}))
    ns = _parse(["tags", "filter", "production", "web01", "ci01", "db01"], store)
    run_tag_command(ns)
    out = capsys.readouterr().out.strip().splitlines()
    assert out == ["web01"]
