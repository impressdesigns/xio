"""The api command."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import niquests
import typer

from xio import api, client, services, tokens

if TYPE_CHECKING:
    from xio.cli.output import RichLog


def _write(text: str) -> None:
    if text:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def api_command(  # noqa: PLR0913 -- one argument per option
    ctx: typer.Context,
    target: Annotated[
        str, typer.Argument(metavar="PATH", help="A path such as /me, or a full URL on a service's host")
    ],
    *,
    method: Annotated[
        str | None, typer.Option("--method", "-X", help="HTTP method (GET, or POST when sending)")
    ] = None,
    raw_fields: Annotated[list[str] | None, typer.Option("--raw-field", "-f", help="A string field, key=value")] = None,
    typed_fields: Annotated[
        list[str] | None,
        typer.Option("--field", "-F", help="A typed field, key=value: true, false, null, a number, or @file"),
    ] = None,
    headers: Annotated[list[str] | None, typer.Option("--header", "-H", help="A request header, name:value")] = None,
    input_file: Annotated[
        str | None, typer.Option("--input", help="A file holding the request body, or - for stdin")
    ] = None,
    paginate: Annotated[bool, typer.Option("--paginate", help="Fetch every page of a list")] = False,
    jq_expression: Annotated[
        str | None, typer.Option("--jq", "-q", help="Filter the response with a jq expression")
    ] = None,
    include: Annotated[bool, typer.Option("--include", "-i", help="Print the status line and headers too")] = False,
    service: Annotated[str | None, typer.Option("--service", "-s", help="Which API to call")] = None,
) -> None:
    """Make an authenticated request, as `gh api` does.

    Fields are the query string of a GET and the JSON body of anything else.
    """
    console: RichLog = ctx.obj
    try:
        fields = [api.parse_field(raw, typed=False) for raw in raw_fields or []]
        fields += [api.parse_field(raw, typed=True) for raw in typed_fields or []]
        body = None
        if input_file is not None:
            body = sys.stdin.buffer.read() if input_file == "-" else Path(input_file).read_bytes()
        request = api.build(
            target,
            service=service,
            method=method,
            fields=fields,
            headers=[api.parse_header(raw) for raw in headers or []],
            body=body,
        )
        query = None if jq_expression is None else api.compile_filter(jq_expression)
        session = client.signed_in(request.service)
        failed = False
        for response in api.send(session, request, paginate=paginate):
            if include:
                _write(api.render_head(response))
            if response.ok:
                _write(api.render(response, query=query, pretty=sys.stdout.isatty()))
            else:
                failed = True
                _write(api.render(response, pretty=sys.stdout.isatty()))
                console.fail(f"{request.service.name} answered HTTP {response.status_code}")
    except (api.UsageError, services.UnknownServiceError, tokens.TokenError, OSError) as error:
        console.fail(str(error))
        raise typer.Exit(code=1) from error
    except niquests.RequestException as error:
        console.fail(f"The request failed: {type(error).__name__}")
        raise typer.Exit(code=1) from error
    if failed:
        raise typer.Exit(code=1)
