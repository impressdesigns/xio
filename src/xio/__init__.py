"""Xio.

A script run with ``xio run`` imports its signed-in clients from here::

    from xio import core

    print(core.get("/me").json())

``core`` is a ``niquests`` session with Core's base URL and a token already set; ``session(name)``
returns the same for any other service.
"""

from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import niquests


@cache
def session(name: str) -> niquests.Session:
    """Return a signed-in session for the service called ``name``, one per process."""
    from xio import client, services  # noqa: PLC0415 -- importing xio must not import an HTTP stack

    return client.signed_in(services.by_name(name))


def __getattr__(name: str) -> niquests.Session:
    if name == "core":
        return session("core")
    message = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(message)
