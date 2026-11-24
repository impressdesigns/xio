"""Test the CLI."""

import json
import sys
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from xio.cli.app import app

if TYPE_CHECKING:
    import pytest

runner = CliRunner()


def test_cli_smoke() -> None:
    """Smoke test for the CLI."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_doctor_prints_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """`doctor` prints JSON that parses back, even with values longer than the console."""
    executable = r"C:\Users\firstname.lastname\AppData\Roaming\uv\tools\xio\Scripts\[x]\python.exe"
    monkeypatch.setattr(sys, "executable", executable)

    result = runner.invoke(app, ["doctor"], env={"COLUMNS": "40"})

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["runtime"]["python"]["executable"] == executable


def test_no_command_shows_help() -> None:
    """`xio` on its own lists its commands."""
    result = runner.invoke(app, [])

    assert "doctor" in result.output
