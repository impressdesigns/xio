"""One authenticated request to a service, shaped like ``gh api``."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jq  # ty: ignore[import-not-found] -- an extension module with no stubs

from xio import services

if TYPE_CHECKING:
    from collections.abc import Iterator

    import niquests

NEXT_LINK_KEYS = ("@odata.nextLink", "nextLink")


class UsageError(ValueError):
    """The request as typed cannot be built."""


def parse_field(raw: str, *, typed: bool) -> tuple[str, Any]:
    """Split ``key=value``. A typed value reads ``true``, ``false``, ``null``, numbers and ``@file``."""
    key, separator, value = raw.partition("=")
    if not separator or not key:
        message = f"A field is key=value, got {raw!r}."
        raise UsageError(message)
    if not typed:
        return key, value
    if value.startswith("@"):
        try:
            return key, Path(value[1:]).read_text()
        except OSError as error:
            message = f"Cannot read {value[1:]}: {error.strerror}."
            raise UsageError(message) from error
    try:
        parsed = json.loads(value)
    except ValueError:
        return key, value
    return key, value if isinstance(parsed, (dict, list, str)) else parsed


def parse_header(raw: str) -> tuple[str, str]:
    """Split ``name: value``."""
    name, separator, value = raw.partition(":")
    if not separator or not name.strip():
        message = f"A header is name:value, got {raw!r}."
        raise UsageError(message)
    return name.strip(), value.strip()


def compile_filter(expression: str) -> Any:  # noqa: ANN401 -- jq ships no types
    """Compile a jq expression."""
    try:
        return jq.compile(expression)
    except ValueError as error:
        message = f"Bad --jq expression: {error}"
        raise UsageError(message) from error


@dataclass(frozen=True, slots=True, kw_only=True)
class Request:
    """A request ready to send."""

    service: services.Service
    method: str
    url: str
    params: dict[str, str] = field(default_factory=dict)
    json: dict[str, Any] | None = None
    body: bytes | None = None
    headers: dict[str, str] = field(default_factory=dict)


def build(  # noqa: PLR0913 -- one argument per option of the command
    target: str,
    *,
    service: str | None = None,
    method: str | None = None,
    fields: list[tuple[str, Any]] | None = None,
    headers: list[tuple[str, str]] | None = None,
    body: bytes | None = None,
) -> Request:
    """Build the request ``gh api`` would: GET unless there is something to send, then POST.

    Fields are the query string of a GET and of any request that carries ``body``; otherwise
    they are the JSON body.
    """
    chosen, url = services.resolve(target, service)
    values = dict(fields or [])
    query = {key: value if isinstance(value, str) else json.dumps(value) for key, value in values.items()}
    sending = bool(values) or body is not None
    verb = (method or ("POST" if sending else "GET")).upper()
    request_headers = dict(headers or [])
    if body is not None:
        if not any(name.lower() == "content-type" for name in request_headers):
            request_headers["Content-Type"] = "application/json"
        return Request(service=chosen, method=verb, url=url, params=query, body=body, headers=request_headers)
    if verb == "GET":
        return Request(service=chosen, method=verb, url=url, params=query, headers=request_headers)
    return Request(service=chosen, method=verb, url=url, json=values or None, headers=request_headers)


def _send(
    session: niquests.Session, request: Request, *, url: str | None = None, offset: int | None = None
) -> niquests.Response:
    params = request.params if url is None else {}
    if offset is not None:
        params = {**params, "offset": str(offset)}
    return session.request(
        request.method,
        url or request.url,
        params=params,
        json=request.json,
        data=request.body,
        headers=request.headers,
    )


def _next_page(request: Request, response: niquests.Response) -> tuple[str | None, int | None] | None:
    """Return where the next page is: a URL, an offset, or nothing when this was the last."""
    try:
        page = response.json()
    except ValueError:
        return None
    if not isinstance(page, dict):
        return None
    for key in NEXT_LINK_KEYS:
        link = page.get(key)
        if isinstance(link, str):
            # A next link is followed only on the service's own host.
            services.resolve(link, request.service.name)
            return link, None
    items, total, offset = page.get("items"), page.get("total"), page.get("offset")
    if (
        isinstance(items, list)
        and isinstance(total, int)
        and isinstance(offset, int)
        and 0 < len(items) < total - offset
    ):
        return None, offset + len(items)
    return None


def send(session: niquests.Session, request: Request, *, paginate: bool = False) -> Iterator[niquests.Response]:
    """Send ``request`` and yield each response: one, or every page of a list when paginating.

    Pages are found two ways: an ``items``/``total``/``offset`` envelope is walked by ``offset``,
    and a body carrying a next link is followed. A failed response ends the walk.
    """
    response = _send(session, request)
    yield response
    while paginate and request.method == "GET" and response.ok:
        following = _next_page(request, response)
        if following is None:
            return
        url, offset = following
        response = _send(session, request, url=url, offset=offset)
        yield response


def render(response: niquests.Response, *, query: Any = None, pretty: bool = False) -> str:  # noqa: ANN401 -- jq ships no types
    """Return what to print for a response: the body, pretty-printed JSON, or the jq results.

    A jq result that is a string prints bare, as ``gh`` and ``jq -r`` do; anything else is one
    line of JSON.
    """
    text = response.text or ""
    if query is None and not pretty:
        return text
    try:
        data = response.json()
    except ValueError:
        return text
    if query is None:
        return json.dumps(data, indent=2, ensure_ascii=False)
    results = query.input_value(data).all()
    return "\n".join(
        result if isinstance(result, str) else json.dumps(result, ensure_ascii=False) for result in results
    )


def render_head(response: niquests.Response) -> str:
    """Return the status line and headers of a response."""
    lines = [f"HTTP {response.status_code} {response.reason or ''}".rstrip()]
    lines += [f"{name}: {value}" for name, value in response.headers.items()]
    return "\n".join(lines) + "\n"
