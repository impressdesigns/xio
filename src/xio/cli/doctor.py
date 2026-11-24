"""Doctor command."""

import json
from enum import Enum
from typing import TYPE_CHECKING, Annotated

import typer

from xio.doctor import generate_report

if TYPE_CHECKING:
    from xio.cli.output import RichLog

app = typer.Typer(
    help="Collect environment information for support diagnostics",
    invoke_without_command=True,
    add_completion=False,
)


class DoctorFormat(Enum):
    """Output format for the doctor report."""

    json = "json"


@app.callback()
def doctor(
    ctx: typer.Context,
    output_format: Annotated[DoctorFormat, typer.Option("--format", "-f", help="Output format")] = DoctorFormat.json,
) -> None:
    """Collect environment information for support diagnostics."""
    console: RichLog = ctx.obj

    report = generate_report()
    match output_format:
        case DoctorFormat.json:
            console.raw(json.dumps(report, indent=2))
