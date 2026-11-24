"""Tests for xio.services."""

import pytest

from xio import services


def test_a_path_goes_to_the_default_service() -> None:
    """A bare path is joined to the default service's base URL."""
    service, url = services.resolve("/me")

    assert service.name == services.DEFAULT_SERVICE
    assert url == f"{service.base_url}/me"


def test_a_path_without_a_leading_slash_is_joined_the_same_way() -> None:
    """`me` and `/me` are the same path."""
    assert services.resolve("me") == services.resolve("/me")


def test_a_named_service_takes_the_path() -> None:
    """--service picks the base URL."""
    service, url = services.resolve("/v1.0/me", "graph")

    assert service.name == "graph"
    assert url == f"{service.base_url}/v1.0/me"


def test_a_full_url_picks_its_service_by_host() -> None:
    """A URL on a service's host needs no --service."""
    graph = services.by_name("graph")

    service, url = services.resolve(f"{graph.base_url}/v1.0/me")

    assert service is graph
    assert url == f"{graph.base_url}/v1.0/me"


def test_a_url_on_a_foreign_host_is_refused() -> None:
    """A token is never sent to a host that is not a service's own."""
    with pytest.raises(services.UnknownServiceError):
        services.resolve("https://example.com/me")


def test_a_url_that_contradicts_the_named_service_is_refused() -> None:
    """A URL for one service with --service naming another is a mistake, not a choice."""
    graph = services.by_name("graph")

    with pytest.raises(services.UnknownServiceError):
        services.resolve(f"{graph.base_url}/v1.0/me", "core")


def test_an_unknown_service_is_refused() -> None:
    """A misspelled service names the ones that exist."""
    with pytest.raises(services.UnknownServiceError, match="core"):
        services.by_name("nope")
