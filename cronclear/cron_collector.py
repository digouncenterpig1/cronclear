"""Collect crontab entries from remote hosts via SSHClient."""

from dataclasses import dataclass, field
from typing import Dict, List

from cronclear.cron_parser import CronEntry, parse_crontab
from cronclear.ssh_client import SSHClient, SSHConnectionConfig


@dataclass
class CollectionResult:
    """Aggregated cron entries and errors from one or more hosts."""

    entries: List[CronEntry] = field(default_factory=list)
    host_errors: Dict[str, str] = field(default_factory=dict)
    parse_errors: Dict[str, List[str]] = field(default_factory=dict)


DEFAULT_CRONTAB_CMD = "crontab -l 2>/dev/null"


class CronCollector:
    """Fetches and parses crontab entries from remote hosts."""

    def __init__(self, command: str = DEFAULT_CRONTAB_CMD) -> None:
        self.command = command

    def collect_from_host(self, config: SSHConnectionConfig) -> CollectionResult:
        """Connect to a single host and collect crontab entries for all users.

        Args:
            config: SSH connection configuration including host and users.

        Returns:
            CollectionResult with parsed entries and any errors.
        """
        result = CollectionResult()
        client = SSHClient(config)

        try:
            client.connect()
        except Exception as exc:  # noqa: BLE001
            result.host_errors[config.host] = str(exc)
            return result

        try:
            users = config.extra_users or []
            # Always collect for the connecting user (None means default)
            for user in [None, *users]:
                effective_user = user or config.username
                cmd = self.command if user is None else f"sudo -u {user} {self.command}"

                try:
                    stdout, stderr, exit_code = client.run_command(cmd)
                except Exception as exc:  # noqa: BLE001
                    key = f"{config.host}:{effective_user}"
                    result.host_errors[key] = str(exc)
                    continue

                if exit_code not in (0, 1):  # exit 1 = no crontab
                    key = f"{config.host}:{effective_user}"
                    result.host_errors[key] = stderr.strip() or f"exit code {exit_code}"
                    continue

                parse_result = parse_crontab(stdout, user=effective_user, host=config.host)
                result.entries.extend(parse_result.entries)

                if parse_result.errors:
                    key = f"{config.host}:{effective_user}"
                    result.parse_errors[key] = parse_result.errors
        finally:
            client.disconnect()

        return result

    def collect_from_hosts(self, configs: List[SSHConnectionConfig]) -> CollectionResult:
        """Collect crontab entries from multiple hosts.

        Args:
            configs: List of SSH connection configurations.

        Returns:
            Merged CollectionResult across all hosts.
        """
        merged = CollectionResult()
        for config in configs:
            partial = self.collect_from_host(config)
            merged.entries.extend(partial.entries)
            merged.host_errors.update(partial.host_errors)
            merged.parse_errors.update(partial.parse_errors)
        return merged
