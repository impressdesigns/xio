"""HTTP sessions for the services."""

import time
from typing import TYPE_CHECKING, Any

import niquests
from niquests.adapters import BaseAdapter

from xio.config import Config
from xio.tokens import get_token

if TYPE_CHECKING:
    from xio.services import Service

UNAUTHORIZED = 401
TOO_MANY_REQUESTS = 429
SERVER_ERROR = 500
REPEATABLE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})


def anonymous(service: Service) -> niquests.Session:
    """Return a session for ``service`` that sends no token."""
    return niquests.Session(base_url=service.base_url, timeout=Config.timeout_seconds)


def signed_in(service: Service) -> niquests.Session:
    """Return a session for ``service`` that sends the signed-in account's token."""
    session = anonymous(service)
    session.headers["Authorization"] = f"Bearer {get_token(service)}"
    return session


def _raise_for_failure(response: niquests.PreparedRequest | niquests.Response, /, **_: object) -> None:
    if isinstance(response, niquests.Response) and not response.ok:
        method = response.request.method if response.request else ""
        message = f"{response.status_code} from {method} {response.url}: {response.text}"
        raise niquests.HTTPError(message, response=response)


def _wait(response: niquests.Response, attempt: int) -> float:
    try:
        asked = float(response.headers.get("Retry-After", ""))
    except ValueError:
        asked = 2.0**attempt
    return min(max(asked, 0), Config.retry_wait_limit_seconds)


class _Persistent(BaseAdapter):
    """Send through another adapter, again when the service throttles, fails or refuses the token.

    A 429 is sent again whatever the method, since the service did nothing with it. A 5xx is
    sent again only for a method that is safe to repeat. A 401 gets one more try with a new
    token, because a long script outlives the token it started with.
    """

    def __init__(self, inner: BaseAdapter, session: niquests.Session, service: Service) -> None:
        super().__init__()
        self.inner = inner
        self.session = session
        self.service = service

    def _renew(self, request: niquests.PreparedRequest) -> None:
        authorization = f"Bearer {get_token(self.service)}"
        self.session.headers["Authorization"] = authorization
        if request.headers is not None:
            request.headers["Authorization"] = authorization

    def send(self, request: niquests.PreparedRequest, *args: Any, **kwargs: Any) -> niquests.Response:  # noqa: ANN401 -- passed through to the adapter underneath
        """Send ``request``, waiting and sending again while that can help."""
        repeatable = request.body is None or isinstance(request.body, (bytes, str))
        renewed = False
        attempt = 0
        while True:
            response = self.inner.send(request, *args, **kwargs)
            status = response.status_code or 0
            if not repeatable:
                return response
            if status == UNAUTHORIZED and not renewed:
                renewed = True
                self._renew(request)
                continue
            attempt += 1
            throttled = status == TOO_MANY_REQUESTS
            failed = status >= SERVER_ERROR and request.method in REPEATABLE_METHODS
            if not (throttled or failed) or attempt >= Config.attempts:
                return response
            time.sleep(_wait(response, attempt))

    def close(self) -> None:
        """Close the adapter underneath."""
        self.inner.close()


def scripting(service: Service) -> niquests.Session:
    """Return a signed-in session for a script.

    A failed response raises, with its body in the message, after a throttled or failed request
    has been sent again and an expired token renewed.
    """
    session = signed_in(service)
    for prefix, adapter in list(session.adapters.items()):
        session.mount(prefix, _Persistent(adapter, session, service))
    session.hooks["response"].append(_raise_for_failure)
    return session
