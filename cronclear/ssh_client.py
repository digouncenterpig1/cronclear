"""SSH client module for connecting to remote hosts and fetching crontab data."""

import logging
from dataclasses import dataclass, field
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)


@dataclass
class SSHConnectionConfig:
    hostname: str
    username: str
    port: int = 22
    password: Optional[str] = None
    key_filepath: Optional[str] = None
    timeout: float = 10.0
    extra_users: list[str] = field(default_factory=list)


class SSHClient:
    def __init__(self, config: SSHConnectionConfig):
        self.config = config
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        """Establish SSH connection to the remote host."""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.config.hostname,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": self.config.timeout,
        }

        if self.config.key_filepath:
            connect_kwargs["key_filename"] = self.config.key_filepath
        elif self.config.password:
            connect_kwargs["password"] = self.config.password

        logger.info("Connecting to %s:%d as %s", self.config.hostname, self.config.port, self.config.username)
        self._client.connect(**connect_kwargs)

    def disconnect(self) -> None:
        """Close the SSH connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Disconnected from %s", self.config.hostname)

    def fetch_crontab(self, user: Optional[str] = None) -> str:
        """Fetch crontab entries for a given user (or current user if None)."""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")

        cmd = f"crontab -u {user} -l" if user else "crontab -l"
        logger.debug("Running command on %s: %s", self.config.hostname, cmd)

        _, stdout, stderr = self._client.exec_command(cmd)
        output = stdout.read().decode("utf-8").strip()
        error = stderr.read().decode("utf-8").strip()

        if error and "no crontab for" not in error.lower():
            logger.warning("stderr from %s (%s): %s", self.config.hostname, cmd, error)

        return output

    def fetch_all_crontabs(self) -> dict[str, str]:
        """Fetch crontabs for the primary user and any extra_users defined in config."""
        results: dict[str, str] = {}
        primary = self.config.username
        results[primary] = self.fetch_crontab()

        for user in self.config.extra_users:
            results[user] = self.fetch_crontab(user=user)

        return results

    def __enter__(self) -> "SSHClient":
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()
