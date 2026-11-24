"""CLI implementation."""

from typing import Annotated

import typer

from xio.cli.api import api_command
from xio.cli.auth import app as auth_app
from xio.cli.doctor import app as doctor_app
from xio.cli.output import RichLog
from xio.cli.run import run_command

app = typer.Typer(name="xio", help="Command-line data helper for Core", no_args_is_help=True, add_completion=False)

app.command(name="api")(api_command)
app.add_typer(auth_app, name="auth")
app.add_typer(doctor_app, name="doctor")
app.command(name="run", context_settings={"allow_interspersed_args": False})(run_command)


@app.callback()
def callback(
    ctx: typer.Context,
    *,
    verbosity: Annotated[int, typer.Option("--verbose", "-v", count=True, help="Increase verbosity (-v, -vv)")] = 0,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Show only warnings and errors (overrides -v)")] = False,
) -> None:
    """CLI entry point with structured verbosity."""
    ctx.obj = RichLog(verbosity=verbosity, quiet=quiet)
