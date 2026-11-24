"""HTTP sessions for the services."""

from typing import TYPE_CHECKING

import niquests

from xio.config import Config
from xio.tokens import get_token

if TYPE_CHECKING:
    from xio.services import Service


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


def scripting(service: Service) -> niquests.Session:
    """Return a signed-in session for a script: a failed response raises, with its body in the message."""
    session = signed_in(service)
    session.hooks["response"].append(_raise_for_failure)
    return session
