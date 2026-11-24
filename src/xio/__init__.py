"""Xio.

A script run with ``xio run`` imports its signed-in clients from here::

    from xio import core

    print(core.get("/me").json())

``core`` is a ``niquests`` session with Core's base URL and a token already set; ``session(name)``
returns the same for any other service. A failed response raises ``niquests.HTTPError``, so a
script needs no ``raise_for_status()``. ``items(path)`` yields every item of a list, page by page.
"""

from functools import cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

    import niquests


@cache
def session(name: str) -> niquests.Session:
    """Return a signed-in session for the service called ``name``, one per process."""
    from xio import client, services  # noqa: PLC0415 -- importing xio must not import an HTTP stack

    return client.scripting(services.by_name(name))


def items(path: str, *, service: str | None = None, **params: object) -> Iterator[Any]:
    """Yield every item of the list at ``path``, fetching each page as it is needed.

    Keyword arguments are the query string: ``items("/sales-orders/", limit=500, status="open")``.
    """
    from xio import api  # noqa: PLC0415 -- importing xio must not import an HTTP stack

    request = api.build(
        path, service=service, method="GET", fields=[(key, str(value)) for key, value in params.items()]
    )
    for response in api.send(session(request.service.name), request, paginate=True):
        page = response.json()
        yield from page["items"] if isinstance(page, dict) else page


def __getattr__(name: str) -> niquests.Session:
    if name == "core":
        return session("core")
    message = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(message)
