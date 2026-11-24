"""Tests for the auth commands."""

import json
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from tests.test_tokens import make_token
from xio import tokens
from xio.cli.app import app

if TYPE_CHECKING:
    import pytest

runner = CliRunner()


def test_token_prints_only_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """`auth token` writes the bare token to standard output, ready for another tool."""
    monkeypatch.setattr(tokens, "get_token", lambda _: "abc")

    result = runner.invoke(app, ["auth", "token"])

    assert result.exit_code == 0
    assert result.stdout == "abc\n"


def test_status_reports_the_account_and_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    """`auth status` prints who is signed in and when the token runs out, as JSON."""
    monkeypatch.setattr(tokens, "account", lambda: "someone@example.com")
    monkeypatch.setattr(tokens, "get_token", lambda _: make_token(exp=1893553445))

    result = runner.invoke(app, ["auth", "status", "--service", "graph"])

    assert result.exit_code == 0
    status = json.loads(result.stdout)
    assert status["account"] == "someone@example.com"
    assert status["service"] == "graph"


def test_status_fails_when_not_signed_in() -> None:
    """With no Azure CLI `auth status` exits non-zero and keeps standard output empty."""
    result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert "not installed" in result.stderr


def test_an_unknown_service_fails() -> None:
    """A misspelled --service is an error, not a traceback."""
    result = runner.invoke(app, ["auth", "token", "--service", "nope"])

    assert result.exit_code == 1
    assert result.stdout == ""
