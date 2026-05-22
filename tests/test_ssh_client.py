"""Tests for the SSH client module."""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from cronclear.ssh_client import SSHClient, SSHConnectionConfig


@pytest.fixture
def basic_config():
    return SSHConnectionConfig(
        hostname="example.com",
        username="admin",
        port=22,
        password="secret",
    )


@pytest.fixture
def config_with_extra_users():
    return SSHConnectionConfig(
        hostname="example.com",
        username="admin",
        extra_users=["deploy", "www-data"],
    )


def _make_exec_result(stdout_text: str, stderr_text: str = ""):
    stdout = MagicMock()
    stdout.read.return_value = stdout_text.encode()
    stderr = MagicMock()
    stderr.read.return_value = stderr_text.encode()
    return MagicMock(), stdout, stderr


@patch("cronclear.ssh_client.paramiko.SSHClient")
def test_connect_uses_password(mock_paramiko_cls, basic_config):
    mock_instance = MagicMock()
    mock_paramiko_cls.return_value = mock_instance

    client = SSHClient(basic_config)
    client.connect()

    mock_instance.connect.assert_called_once_with(
        hostname="example.com",
        port=22,
        username="admin",
        timeout=10.0,
        password="secret",
    )


@patch("cronclear.ssh_client.paramiko.SSHClient")
def test_connect_uses_key_file(mock_paramiko_cls):
    config = SSHConnectionConfig(hostname="h", username="u", key_filepath="/home/u/.ssh/id_rsa")
    mock_instance = MagicMock()
    mock_paramiko_cls.return_value = mock_instance

    SSHClient(config).connect()

    call_kwargs = mock_instance.connect.call_args.kwargs
    assert call_kwargs["key_filename"] == "/home/u/.ssh/id_rsa"
    assert "password" not in call_kwargs


@patch("cronclear.ssh_client.paramiko.SSHClient")
def test_fetch_crontab_returns_output(mock_paramiko_cls, basic_config):
    mock_instance = MagicMock()
    mock_paramiko_cls.return_value = mock_instance
    mock_instance.exec_command.return_value = _make_exec_result("0 * * * * /usr/bin/backup")

    client = SSHClient(basic_config)
    client._client = mock_instance
    result = client.fetch_crontab()

    assert result == "0 * * * * /usr/bin/backup"
    mock_instance.exec_command.assert_called_once_with("crontab -l")


@patch("cronclear.ssh_client.paramiko.SSHClient")
def test_fetch_crontab_with_user(mock_paramiko_cls, basic_config):
    mock_instance = MagicMock()
    mock_paramiko_cls.return_value = mock_instance
    mock_instance.exec_command.return_value = _make_exec_result("*/5 * * * * /deploy/run")

    client = SSHClient(basic_config)
    client._client = mock_instance
    result = client.fetch_crontab(user="deploy")

    assert result == "*/5 * * * * /deploy/run"
    mock_instance.exec_command.assert_called_once_with("crontab -u deploy -l")


@patch("cronclear.ssh_client.paramiko.SSHClient")
def test_fetch_all_crontabs(mock_paramiko_cls, config_with_extra_users):
    mock_instance = MagicMock()
    mock_paramiko_cls.return_value = mock_instance
    mock_instance.exec_command.side_effect = [
        _make_exec_result("0 1 * * * admin_job"),
        _make_exec_result("0 2 * * * deploy_job"),
        _make_exec_result(""),
    ]

    client = SSHClient(config_with_extra_users)
    client._client = mock_instance
    results = client.fetch_all_crontabs()

    assert results["admin"] == "0 1 * * * admin_job"
    assert results["deploy"] == "0 2 * * * deploy_job"
    assert results["www-data"] == ""


def test_fetch_crontab_raises_when_not_connected(basic_config):
    client = SSHClient(basic_config)
    with pytest.raises(RuntimeError, match="Not connected"):
        client.fetch_crontab()
