"""The APIs Xio can call: a base URL and the token scope that opens it."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from xio.config import Config


@dataclass(frozen=True, slots=True)
class Service:
    """One API."""

    name: str
    base_url: str
    scope: str


SERVICES = {
    service.name: service
    for service in (
        Service("core", Config.core_url.rstrip("/"), Config.core_scope),
        Service("local-api", Config.local_api_url.rstrip("/"), Config.local_api_scope),
        Service("graph", Config.graph_url.rstrip("/"), Config.graph_scope),
        Service("arm", Config.arm_url.rstrip("/"), Config.arm_scope),
    )
}


class UnknownServiceError(LookupError):
    """No service has this name or serves this URL."""


def by_name(name: str) -> Service:
    """Return the service called ``name``."""
    try:
        return SERVICES[name]
    except KeyError:
        msg = f"Unknown service {name!r}; choose from {', '.join(SERVICES)}."
        raise UnknownServiceError(msg) from None


def by_url(url: str) -> Service:
    """Return the service whose host serves ``url``."""
    host = urlsplit(url).netloc
    for service in SERVICES.values():
        if urlsplit(service.base_url).netloc == host:
            return service
    msg = f"No service is served from {host!r}; choose from {', '.join(SERVICES)}."
    raise UnknownServiceError(msg)


def resolve(target: str, name: str | None = None) -> tuple[Service, str]:
    """Return the service and full URL for a path or URL.

    A full URL picks its service by host, and never goes to a host that is not a service's own.
    """
    if target.startswith(("https://", "http://")):
        service = by_url(target)
        if name is not None and name != service.name:
            msg = f"{target} belongs to {service.name!r}, not {name!r}."
            raise UnknownServiceError(msg)
        return service, target
    service = by_name(name or Config.default_service)
    return service, f"{service.base_url}/{target.lstrip('/')}"
