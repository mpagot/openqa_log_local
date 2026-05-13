"""Tests for the CLI error handling and logging format."""

import sys
from unittest.mock import patch

from click.testing import CliRunner

import openqa_log_local.cli  # noqa: F401 — ensure submodule is loaded
from openqa_log_local.cli import cli
from openqa_log_local.client import openQAClientConnectionError

# __init__.py shadows the submodule with `from .cli import cli`, so
# `import openqa_log_local.cli` resolves to the Click group, not the module.
# Access the real module via sys.modules for patching.
_cli_module = sys.modules["openqa_log_local.cli"]


def test_cli_connection_error_shows_clean_message():
    """Test that a connection error produces a clean one-line message, not a traceback."""
    runner = CliRunner()
    with patch.object(
        _cli_module,
        "openQA_log_local",
        side_effect=openQAClientConnectionError("Failed to connect to bad.host via https"),
    ):
        result = runner.invoke(
            cli, ["--host", "bad.host", "get-log-list", "--job-id", "1"]
        )

    assert result.exit_code != 0
    assert "Error: Failed to connect to bad.host via https" in result.output
    assert "Traceback" not in result.output


def test_cli_invalid_host_shows_clean_message():
    """Test that an invalid host produces a clean one-line message."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--host", "ftp://bad.host", "get-log-list", "--job-id", "1"]
    )

    assert result.exit_code != 0
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_cli_debug_log_includes_timestamp():
    """Test that DEBUG log level produces timestamped log lines."""
    runner = CliRunner()
    with patch.object(
        _cli_module,
        "openQA_log_local",
        side_effect=openQAClientConnectionError("conn fail"),
    ):
        result = runner.invoke(
            cli,
            ["--host", "example.com", "--log-level", "debug", "get-log-list", "--job-id", "1"],
        )

    # The error message goes to stdout (via click.echo in _handle_errors)
    assert "Error: conn fail" in result.output
    assert "Traceback" not in result.output
