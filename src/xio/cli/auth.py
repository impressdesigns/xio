"""Auth commands."""

import json
from typing import TYPE_CHECKING, Annotated

import typer

from xio import services, tokens

if TYPE_CHECKING:
    from xio.cli.output import RichLog

app = typer.Typer(help="Sign in and get tokens", no_args_is_help=True, add_completion=False)

ServiceOption = Annotated[str, typer.Option("--service", "-s", help="Which API the token is for")]


@app.command()
def login(ctx: typer.Context) -> None:
    """Sign in through the Azure CLI."""
    console: RichLog = ctx.obj
    try:
        code = tokens.login()
    except tokens.TokenError as error:
        console.fail(str(error))
        raise typer.Exit(code=1) from error
    raise typer.Exit(code=code)


@app.command()
def status(ctx: typer.Context, service: ServiceOption = services.DEFAULT_SERVICE) -> None:
    """Show who is signed in and whether a token can be had."""
    console: RichLog = ctx.obj
    try:
        chosen = services.by_name(service)
        account = tokens.account()
        expires = tokens.expiry(tokens.get_token(chosen))
    except (services.UnknownServiceError, tokens.TokenError) as error:
        console.fail(str(error))
        raise typer.Exit(code=1) from error
    console.raw(
        json.dumps({"account": account, "service": chosen.name, "token_expires": expires.isoformat()}, indent=2)
    )


@app.command()
def token(ctx: typer.Context, service: ServiceOption = services.DEFAULT_SERVICE) -> None:
    """Print a bearer token."""
    console: RichLog = ctx.obj
    try:
        console.raw(tokens.get_token(services.by_name(service)))
    except (services.UnknownServiceError, tokens.TokenError) as error:
        console.fail(str(error))
        raise typer.Exit(code=1) from error
