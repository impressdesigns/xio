"""Tests for xio.config."""

from typing import TYPE_CHECKING

from xio import config

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_every_setting_reads_its_xio_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A setting called name is overridden by XIO_NAME."""
    for name in type(config.Config).model_fields:
        monkeypatch.setenv(f"XIO_{name.upper()}", "7")

    settings = type(config.Config)()

    assert settings.model_dump() == dict.fromkeys(type(settings).model_fields, "7") | {
        "timeout_seconds": 7.0,
        "attempts": 7,
        "retry_wait_limit_seconds": 7.0,
    }


def test_the_defaults_stand_without_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no XIO_ variable set, Core is the default service."""
    for name in type(config.Config).model_fields:
        monkeypatch.delenv(f"XIO_{name.upper()}", raising=False)

    settings = type(config.Config)()

    assert settings.default_service == "core"
    assert settings.core_scope == f"{settings.core_url}/.default"


def test_a_dotenv_file_is_not_read(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A .env in the working directory cannot point a token at another host."""
    monkeypatch.delenv("XIO_CORE_URL", raising=False)
    (tmp_path / ".env").write_text("XIO_CORE_URL=https://elsewhere.test\n")
    monkeypatch.chdir(tmp_path)

    assert type(config.Config)().core_url == config.Config.core_url
