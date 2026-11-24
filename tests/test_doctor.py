"""Tests for xio.doctor."""

from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from xio import doctor
from xio.doctor import generate_report

if TYPE_CHECKING:
    import pytest


def test_generate_report_shape() -> None:
    """The report contains the expected nested sections and keys."""
    report = generate_report()

    assert set(report) == {"timestamp", "tool", "system", "runtime", "checks"}
    assert set(report["tool"]) == {"name", "version", "build", "commit"}
    assert report["tool"]["name"] == "xio"
    assert set(report["system"]) == {"os", "arch"}
    assert set(report["system"]["os"]) == {"name", "version", "release"}
    assert set(report["runtime"]["python"]) == {"version", "implementation", "executable"}


def test_generate_report_timestamp_is_iso8601() -> None:
    """The report timestamp parses as an ISO-8601 datetime."""
    report = generate_report()

    parsed = datetime.fromisoformat(report["timestamp"])
    assert parsed.tzinfo is not None


def test_tool_version_matches_installed_metadata() -> None:
    """The reported version comes from installed package metadata."""
    report = generate_report()

    assert report["tool"]["version"] == version("idi-xio")


def test_tool_version_falls_back_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the package is not installed, the version falls back to 'unknown'."""

    def raise_not_found(name: str) -> str:
        raise PackageNotFoundError(name)

    monkeypatch.setattr(doctor, "version", raise_not_found)

    assert generate_report()["tool"]["version"] == "unknown"


def test_checks_report_a_missing_azure_cli() -> None:
    """With no Azure CLI the checks that need it fail and say why, without raising."""
    assert not doctor.check_azure_cli()["ok"]

    signed_in = doctor.check_signed_in()

    assert not signed_in["ok"]
    assert "not installed" in signed_in["detail"]
