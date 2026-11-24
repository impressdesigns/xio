"""The run command."""

from pathlib import Path  # noqa: TC003 -- Typer reads the annotation when the command runs
from typing import TYPE_CHECKING, Annotated

import typer

from xio.run import run_script

if TYPE_CHECKING:
    from xio.cli.output import RichLog


def run_command(
    ctx: typer.Context,
    script: Annotated[Path, typer.Argument(help="A Python script")],
    arguments: Annotated[list[str] | None, typer.Argument(help="Arguments passed to the script")] = None,
) -> None:
    """Run a script in Xio's environment, where `from xio import core` is a signed-in client.

    The script needs no dependency header and makes no environment of its own.
    """
    console: RichLog = ctx.obj
    if not script.is_file():
        console.fail(f"{script} is not a file.")
        raise typer.Exit(code=1)
    run_script(script, arguments or [])
