"""Diagnostic report generation for support and troubleshooting."""

import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import TypedDict

import niquests

from xio import client, services, tokens


class ToolInfo(TypedDict):
    """Information about the tool itself."""

    name: str
    version: str
    build: str
    commit: str | None


class OSInfo(TypedDict):
    """Operating system information."""

    name: str
    version: str
    release: str


class SystemInfo(TypedDict):
    """Information about the system environment."""

    os: OSInfo
    arch: str


class PythonInfo(TypedDict):
    """Information about the Python interpreter."""

    version: str
    implementation: str
    executable: str


class RuntimeInfo(TypedDict):
    """Information about the runtime environment."""

    python: PythonInfo


class Check(TypedDict):
    """One thing Xio needs, and whether it is there."""

    name: str
    ok: bool
    detail: str


class Report(TypedDict):
    """A full diagnostic report."""

    timestamp: str
    tool: ToolInfo
    system: SystemInfo
    runtime: RuntimeInfo
    checks: list[Check]


def _tool_version() -> str:
    """Return the installed ``idi-xio`` version, or a fallback when not installed."""
    try:
        return version("idi-xio")
    except PackageNotFoundError:
        return "unknown"


def collect_tool_info() -> ToolInfo:
    """Collect basic information about the tool itself."""
    return {
        "name": "xio",
        "version": _tool_version(),
        "build": "dev",
        "commit": None,
    }


def collect_system_info() -> SystemInfo:
    """Collect basic information about the system environment."""
    return {
        "os": {
            "name": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
        },
        "arch": platform.machine(),
    }


def collect_runtime_info() -> RuntimeInfo:
    """Collect basic information about the runtime environment."""
    return {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        }
    }


def check_azure_cli() -> Check:
    """Check that the Azure CLI is installed."""
    path = tokens.azure_cli()
    return {"name": "azure_cli", "ok": path is not None, "detail": path or "az is not on the PATH"}


def check_signed_in() -> Check:
    """Check that the Azure CLI is signed in."""
    try:
        return {"name": "signed_in", "ok": True, "detail": tokens.account()}
    except tokens.TokenError as error:
        return {"name": "signed_in", "ok": False, "detail": str(error)}


def check_token(service: services.Service) -> Check:
    """Check that a token for ``service`` can be had."""
    name = f"{service.name}_token"
    try:
        expires = tokens.expiry(tokens.get_token(service))
    except tokens.TokenError as error:
        return {"name": name, "ok": False, "detail": str(error)}
    return {"name": name, "ok": True, "detail": f"expires {expires.isoformat()}"}


def check_reachable(service: services.Service, path: str) -> Check:
    """Check that ``service`` answers without a token."""
    name = f"{service.name}_reachable"
    try:
        response = client.anonymous(service).get(path, timeout=10)
    except niquests.RequestException as error:
        return {"name": name, "ok": False, "detail": type(error).__name__}
    return {"name": name, "ok": bool(response.ok), "detail": f"HTTP {response.status_code}"}


def run_checks() -> list[Check]:
    """Check everything Xio needs to call Core."""
    core = services.by_name("core")
    return [check_azure_cli(), check_signed_in(), check_token(core), check_reachable(core, "/health")]


def generate_report() -> Report:
    """Generate a diagnostic report with collected information."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool": collect_tool_info(),
        "system": collect_system_info(),
        "runtime": collect_runtime_info(),
        "checks": run_checks(),
    }
