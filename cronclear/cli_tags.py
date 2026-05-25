"""CLI sub-commands for tag management (add / remove / list / filter)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronclear.tag_manager import TagManager

_DEFAULT_STORE = Path("~/.cronclear_tags.json").expanduser()


def build_tag_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    tag_p = subparsers.add_parser("tags", help="Manage host tags")
    tag_sub = tag_p.add_subparsers(dest="tag_cmd", required=True)

    # add
    p_add = tag_sub.add_parser("add", help="Add a tag to a host")
    p_add.add_argument("host")
    p_add.add_argument("tag")

    # remove
    p_rm = tag_sub.add_parser("remove", help="Remove a tag from a host")
    p_rm.add_argument("host")
    p_rm.add_argument("tag")

    # list
    p_ls = tag_sub.add_parser("list", help="List tags for a host (or all hosts)")
    p_ls.add_argument("host", nargs="?", default=None)

    # filter
    p_filter = tag_sub.add_parser("filter", help="Print hosts that carry a tag")
    p_filter.add_argument("tag")
    p_filter.add_argument("hosts", nargs="+")

    for p in (p_add, p_rm, p_ls, p_filter):
        p.add_argument(
            "--store",
            default=str(_DEFAULT_STORE),
            help="Path to tag store JSON file",
        )


def _load_tag_manager(args: argparse.Namespace) -> TagManager:
    """Instantiate a TagManager from the store path in *args*.

    Exits with a helpful message if the store file exists but cannot be read
    (e.g. permission error or malformed JSON).
    """
    store = Path(args.store)
    try:
        return TagManager(store_path=store)
    except (OSError, ValueError) as exc:
        print(f"error: could not load tag store '{store}': {exc}", file=sys.stderr)
        sys.exit(1)


def run_tag_command(args: argparse.Namespace) -> int:
    tm = _load_tag_manager(args)

    if args.tag_cmd == "add":
        tm.add_tag(args.host, args.tag)
        tm.save()
        print(f"Tagged '{args.host}' with '{args.tag}'.")

    elif args.tag_cmd == "remove":
        removed = tm.remove_tag(args.host, args.tag)
        if removed:
            tm.save()
            print(f"Removed tag '{args.tag}' from '{args.host}'.")
        else:
            print(f"Tag '{args.tag}' not found on '{args.host}'.")
            return 1

    elif args.tag_cmd == "list":
        if args.host:
            tags = tm.tags_for(args.host)
            print(f"{args.host}: {', '.join(tags) if tags else '(none)'}")
        else:
            for tag in tm.all_tags():
                hosts = tm.hosts_with_tag(tag)
                print(f"{tag}: {', '.join(hosts)}")

    elif args.tag_cmd == "filter":
        matched = tm.filter_hosts(args.hosts, args.tag)
        for h in matched:
            print(h)

    return 0
