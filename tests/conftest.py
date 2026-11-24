"""Fixtures every test gets."""

import pytest

from xio import doctor, tokens


@pytest.fixture(autouse=True)
def no_outside_world(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the suite off the Azure CLI and the network unless a test puts a stand-in there."""
    monkeypatch.setattr(tokens, "azure_cli", lambda: None)
    monkeypatch.setattr(doctor, "run_checks", list)
