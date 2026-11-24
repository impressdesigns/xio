"""A stand-in service for the tests: a WSGI application that records what it was sent."""

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

import niquests

from xio import services

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

SERVICE = services.Service("core", "https://service.test", "https://service.test/.default")

type Reply = tuple[int, Any]
type Handler = Callable[[dict[str, Any]], Reply]


def echo(seen: dict[str, Any]) -> Reply:
    """Answer with the request as the server saw it."""
    return 200, seen


class Server:
    """A stand-in service that records what it was sent."""

    def __init__(self, handler: Handler = echo) -> None:
        self.handler = handler
        self.requests: list[dict[str, Any]] = []
        self.headers: list[tuple[str, str]] = []

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., object]) -> Iterable[bytes]:
        """Serve one request as a WSGI application."""
        seen = {
            "method": environ["REQUEST_METHOD"],
            "path": environ["PATH_INFO"],
            "query": {key: values[-1] for key, values in parse_qs(environ["QUERY_STRING"]).items()},
            "body": environ["wsgi.input"].read().decode(),
            "content_type": environ.get("CONTENT_TYPE"),
            "authorization": environ.get("HTTP_AUTHORIZATION"),
            "x_test": environ.get("HTTP_X_TEST"),
        }
        self.requests.append(seen)
        status, reply = self.handler(seen)
        body = reply if isinstance(reply, bytes) else json.dumps(reply).encode()
        start_response(
            f"{status} Status", [("Content-Type", "application/json"), ("X-Served-By", "stand-in"), *self.headers]
        )
        return [body]

    def session(self) -> niquests.Session:
        """Return a session whose requests to the stand-in's host land here."""
        session = niquests.Session(app=self)
        session.mount(SERVICE.base_url, session.get_adapter("wsgi://default"))
        session.headers["Authorization"] = "Bearer stand-in"
        return session


def paged(rows: list[int], page_size: int) -> Handler:
    """Serve ``rows`` in the list envelope, ``page_size`` at a time."""

    def handler(seen: dict[str, Any]) -> Reply:
        offset = int(seen["query"].get("offset", 0))
        return 200, {
            "items": rows[offset : offset + page_size],
            "total": len(rows),
            "limit": page_size,
            "offset": offset,
        }

    return handler
