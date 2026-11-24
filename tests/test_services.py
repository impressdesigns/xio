"""Tests for xio.services."""

import pytest

from xio import services


def test_a_path_goes_to_the_default_service() -> None:
    """A bare path is joined to the default service's base URL."""
    service, url = services.resolve("/me")

    assert service.name == "core"
    assert url == f"{service.base_url}/me"


def test_a_path_without_a_leading_slash_is_joined_the_same_way() -> None:
    """`me` and `/me` are the same path."""
    assert services.resolve("me") == services.resolve("/me")


def test_a_named_service_takes_the_path(other: services.Service) -> None:
    """--service picks the base URL."""
    service, url = services.resolve("/v1.0/me", "other")

    assert service is other
    assert url == f"{other.base_url}/v1.0/me"


def test_a_full_url_picks_its_service_by_host(other: services.Service) -> None:
    """A URL on a service's host needs no --service."""
    service, url = services.resolve(f"{other.base_url}/v1.0/me")

    assert service is other
    assert url == f"{other.base_url}/v1.0/me"


def test_a_url_on_a_foreign_host_is_refused() -> None:
    """A token is never sent to a host that is not a service's own."""
    with pytest.raises(services.UnknownServiceError):
        services.resolve("https://example.com/me")


def test_a_url_that_contradicts_the_named_service_is_refused(other: services.Service) -> None:
    """A URL for one service with --service naming another is a mistake, not a choice."""
    with pytest.raises(services.UnknownServiceError):
        services.resolve(f"{other.base_url}/v1.0/me", "core")


def test_an_unknown_service_is_refused() -> None:
    """A misspelled service names the ones that exist."""
    with pytest.raises(services.UnknownServiceError, match="core"):
        services.by_name("nope")
