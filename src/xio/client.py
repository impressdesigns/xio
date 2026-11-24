"""HTTP sessions for the services."""

from typing import TYPE_CHECKING

import niquests

from xio.tokens import get_token

if TYPE_CHECKING:
    from xio.services import Service

TIMEOUT_SECONDS = 60


def anonymous(service: Service) -> niquests.Session:
    """Return a session for ``service`` that sends no token."""
    return niquests.Session(base_url=service.base_url, timeout=TIMEOUT_SECONDS)


def signed_in(service: Service) -> niquests.Session:
    """Return a session for ``service`` that sends the signed-in account's token."""
    session = anonymous(service)
    session.headers["Authorization"] = f"Bearer {get_token(service)}"
    return session
