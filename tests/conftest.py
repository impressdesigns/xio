"""Fixtures every test gets."""

import pytest

from xio import doctor, services, tokens


@pytest.fixture(autouse=True)
def no_outside_world(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the suite off the Azure CLI and the network unless a test puts a stand-in there."""
    monkeypatch.setattr(tokens, "azure_cli", lambda: None)
    monkeypatch.setattr(doctor, "run_checks", list)


@pytest.fixture
def other(monkeypatch: pytest.MonkeyPatch) -> services.Service:
    """Register a second service, so choosing between services has something to choose."""
    service = services.Service("other", "https://other.test", "https://other.test/.default")
    monkeypatch.setitem(services.SERVICES, service.name, service)
    return service
