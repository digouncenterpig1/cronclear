"""CLI entry point for cronclear."""

import sys
import argparse
from typing import List

from cronclear.ssh_client import SSHConnectionConfig
from cronclear.cron_collector import CronCollector
from cronclear.schedule_analyzer import analyze
from cronclear.reporter import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronclear",
        description="Audit and visualize crontab schedules across remote hosts via SSH.",
    )
    parser.add_argument("hosts", nargs="+", help="Remote host(s) to audit")
    parser.add_argument("-u", "--user", default="root", help="SSH username (default: root)")
    parser.add_argument("-p", "--password", default=None, help="SSH password")
    parser.add_argument("-k", "--key-file", default=None, dest="key_file", help="Path to SSH private key")
    parser.add_argument("--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument(
        "--extra-users",
        nargs="*",
        default=[],
        dest="extra_users",
        help="Additional users whose crontabs to collect",
    )
    return parser


def run(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configs = [
        SSHConnectionConfig(
            host=host,
            username=args.user,
            password=args.password,
            key_file=args.key_file,
            port=args.port,
            extra_users=args.extra_users,
        )
        for host in args.hosts
    ]

    collector = CronCollector(configs)
    results = collector.collect_from_hosts()

    if not results:
        print("No results collected. Check connectivity and permissions.", file=sys.stderr)
        return 1

    report = analyze(results)
    render_report(report)
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
