"""Tests for xio.run, the run command and the clients a script imports."""

import sys
from typing import TYPE_CHECKING

from typer.testing import CliRunner

from xio import client, session
from xio.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

runner = CliRunner()


def test_a_script_runs_as_main_with_its_arguments(tmp_path: Path) -> None:
    """The script sees itself as __main__ and gets its own arguments, options included."""
    script = tmp_path / "script.py"
    script.write_text("import sys\nif __name__ == '__main__':\n    print('|'.join(sys.argv[1:]))\n")

    result = runner.invoke(app, ["run", str(script), "one", "--flag", "-x", "two"])

    assert result.exit_code == 0
    assert result.stdout == "one|--flag|-x|two\n"


def test_a_script_imports_modules_beside_it(tmp_path: Path) -> None:
    """A helper module in the script's folder is importable, as with `python script.py`."""
    (tmp_path / "helper_beside_the_script.py").write_text("VALUE = 'beside'\n")
    script = tmp_path / "script.py"
    script.write_text("import helper_beside_the_script\nprint(helper_beside_the_script.VALUE)\n")

    result = runner.invoke(app, ["run", str(script)])

    assert result.stdout == "beside\n"


def test_the_callers_arguments_and_path_are_put_back(tmp_path: Path) -> None:
    """Running a script leaves sys.argv and sys.path as they were."""
    script = tmp_path / "script.py"
    script.write_text("pass\n")
    arguments, path = sys.argv[:], sys.path[:]

    runner.invoke(app, ["run", str(script), "x"])

    assert sys.argv == arguments
    assert sys.path == path


def test_a_scripts_exit_code_is_the_commands(tmp_path: Path) -> None:
    """sys.exit in the script sets the exit code of `xio run`."""
    script = tmp_path / "script.py"
    script.write_text("import sys\nsys.exit(3)\n")

    result = runner.invoke(app, ["run", str(script)])

    assert result.exit_code == 3


def test_a_missing_script_fails() -> None:
    """A path that is not a file is an error."""
    result = runner.invoke(app, ["run", "no-such-script.py"])

    assert result.exit_code == 1


def test_a_script_gets_a_signed_in_core_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`from xio import core` is the signed-in session for Core, made once."""
    made: list[str] = []

    def signed_in(service: object) -> str:
        made.append(getattr(service, "name", ""))
        return "the-core-session"

    monkeypatch.setattr(client, "signed_in", signed_in)
    session.cache_clear()
    script = tmp_path / "script.py"
    script.write_text("from xio import core\nimport xio\nprint(core, xio.core is core)\n")

    result = runner.invoke(app, ["run", str(script)])
    session.cache_clear()

    assert result.stdout == "the-core-session True\n"
    assert made == ["core"]
