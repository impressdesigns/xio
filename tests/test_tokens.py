"""Tests for xio.tokens."""

import base64
import json
import subprocess
from datetime import UTC, datetime

import pytest

from xio import services, tokens


def make_token(**claims: object) -> str:
    """Build an unsigned JWT carrying ``claims``."""
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


def stand_in_for_az(
    monkeypatch: pytest.MonkeyPatch, *, returncode: int = 0, stdout: str = "", stderr: str = ""
) -> list[list[str]]:
    """Replace the Azure CLI with a canned result and return the commands it was given."""
    commands: list[list[str]] = []

    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, returncode, stdout, stderr)

    monkeypatch.setattr(tokens, "azure_cli", lambda: "az")
    monkeypatch.setattr(subprocess, "run", run)
    return commands


def test_get_token_asks_az_for_the_services_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """The token comes from az, for the scope of the service asked for."""
    commands = stand_in_for_az(monkeypatch, stdout=json.dumps({"accessToken": "abc"}))
    graph = services.by_name("graph")

    assert tokens.get_token(graph) == "abc"
    assert graph.scope in commands[0]


def test_a_failed_az_call_says_how_to_sign_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """When az fails the error carries its last line and the command that fixes it."""
    stand_in_for_az(monkeypatch, returncode=1, stderr="WARNING: noise\nERROR: Please run 'az login'")

    with pytest.raises(tokens.TokenError, match="xio auth login") as raised:
        tokens.get_token(services.by_name("core"))

    assert "Please run 'az login'" in str(raised.value)


def test_a_missing_az_is_a_token_error() -> None:
    """Without the Azure CLI there is no token, and the error says so."""
    with pytest.raises(tokens.TokenError, match="not installed"):
        tokens.account()


def test_account_reads_the_signed_in_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The account is the user name az reports."""
    stand_in_for_az(monkeypatch, stdout=json.dumps({"user": {"name": "someone@example.com"}}))

    assert tokens.account() == "someone@example.com"


def test_expiry_reads_the_exp_claim() -> None:
    """A token's expiry is its exp claim, in UTC."""
    moment = datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC)

    assert tokens.expiry(make_token(exp=int(moment.timestamp()))) == moment


def test_claims_refuses_something_that_is_not_a_jwt() -> None:
    """An opaque string is a token error, not a crash."""
    with pytest.raises(tokens.TokenError):
        tokens.claims("not-a-token")
