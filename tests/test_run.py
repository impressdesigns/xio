"""Tests for xio.run, the run command and the clients a script imports."""

import sys
import time
from typing import TYPE_CHECKING, Any

import niquests
import pytest
from typer.testing import CliRunner

import xio
import xio.client
from tests.stand_in import paged
from xio.cli.app import app
from xio.config import Config

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from tests.stand_in import Handler, Server

runner = CliRunner()


def test_a_script_runs_as_main_with_its_arguments(tmp_path: Path) -> None:
    """The script sees itself as __main__ and gets its own arguments, options included."""
    script = tmp_path / "script.py"
    script.write_text("import sys\nif __name__ == '__main__':\n    print('|'.join(sys.argv[1:]))\n")

    result = runner.invoke(app, ["run", str(script), "one", "--flag", "-x", "two"])

    assert result.exit_code == 0
    assert result.stdout == "one|--flag|-x|two\n"


def test_a_script_imports_modules_beside_it(tmp_path: Path) -> None:
    """A helper module in the script's folder is importable, as with `python script.py`."""
    (tmp_path / "helper_beside_the_script.py").write_text("VALUE = 'beside'\n")
    script = tmp_path / "script.py"
    script.write_text("import helper_beside_the_script\nprint(helper_beside_the_script.VALUE)\n")

    result = runner.invoke(app, ["run", str(script)])

    assert result.stdout == "beside\n"


def test_the_callers_arguments_and_path_are_put_back(tmp_path: Path) -> None:
    """Running a script leaves sys.argv and sys.path as they were."""
    script = tmp_path / "script.py"
    script.write_text("pass\n")
    arguments, path = sys.argv[:], sys.path[:]

    runner.invoke(app, ["run", str(script), "x"])

    assert sys.argv == arguments
    assert sys.path == path


def test_a_scripts_exit_code_is_the_commands(tmp_path: Path) -> None:
    """sys.exit in the script sets the exit code of `xio run`."""
    script = tmp_path / "script.py"
    script.write_text("import sys\nsys.exit(3)\n")

    result = runner.invoke(app, ["run", str(script)])

    assert result.exit_code == 3


def test_a_missing_script_fails() -> None:
    """A path that is not a file is an error."""
    result = runner.invoke(app, ["run", "no-such-script.py"])

    assert result.exit_code == 1


def test_a_script_gets_a_signed_in_core_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`from xio import core` is the signed-in session for Core, made once."""
    made: list[str] = []

    def signed_in(service: object) -> str:
        made.append(getattr(service, "name", ""))
        return "the-core-session"

    monkeypatch.setattr(xio.client, "scripting", signed_in)
    xio.session.cache_clear()
    script = tmp_path / "script.py"
    script.write_text("from xio import core\nimport xio\nprint(core, xio.core is core)\n")

    result = runner.invoke(app, ["run", str(script)])
    xio.session.cache_clear()

    assert result.stdout == "the-core-session True\n"
    assert made == ["core"]


@pytest.fixture
def core(server: Server) -> Iterator[Server]:
    """Make `xio.core` a fresh session against the stand-in."""
    xio.session.cache_clear()
    yield server
    xio.session.cache_clear()


def test_a_failed_response_raises_with_its_body(core: Server) -> None:
    """A script needs no raise_for_status: the client raises, and the message carries the body."""
    core.handler = lambda _: (404, {"detail": "No such order."})

    with pytest.raises(niquests.HTTPError, match=r"404 from GET .*No such order") as raised:
        xio.core.get("/sales-orders/1")

    assert raised.value.response is not None
    assert raised.value.response.json() == {"detail": "No such order."}


@pytest.mark.usefixtures("core")
def test_a_successful_response_is_returned() -> None:
    """A response that is not a failure comes back as usual."""
    assert xio.core.get("/me").json()["path"] == "/me"


def test_items_yields_every_item_of_every_page(core: Server) -> None:
    """`items` walks the list envelope, sending its keyword arguments as the query."""
    core.handler = paged(list(range(7)), 3)

    assert list(xio.items("/things/", limit=3, status="open")) == list(range(7))
    assert [seen["query"].get("offset") for seen in core.requests] == [None, "3", "6"]
    assert all(seen["query"]["status"] == "open" for seen in core.requests)


def test_items_fetches_a_page_only_when_it_is_reached(core: Server) -> None:
    """Stopping early stops the requests."""
    core.handler = paged(list(range(7)), 3)

    assert next(iter(xio.items("/things/"))) == 0
    assert len(core.requests) == 1


def test_items_of_a_bare_list_are_its_elements(core: Server) -> None:
    """A route that answers with a plain list yields its elements."""
    core.handler = lambda _: (200, [1, 2])

    assert list(xio.items("/things/")) == [1, 2]


def test_items_raises_when_a_page_fails(core: Server) -> None:
    """A failed page raises instead of ending the list quietly."""
    core.handler = lambda _: (500, {"detail": "boom"})

    with pytest.raises(niquests.HTTPError):
        list(xio.items("/things/"))


@pytest.fixture
def waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record the waits between attempts instead of sleeping through them."""
    waited: list[float] = []
    monkeypatch.setattr(time, "sleep", waited.append)
    return waited


def answers(*replies: tuple[int, object]) -> Handler:
    """Serve ``replies`` in turn, then the last one for good."""
    remaining = list(replies)

    def handler(_: dict[str, Any]) -> tuple[int, object]:
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    return handler


def test_a_throttled_request_is_sent_again(core: Server, waits: list[float]) -> None:
    """A 429 is retried whatever the method, since the service did nothing with it."""
    core.handler = answers((429, {}), (429, {}), (200, {"ok": True}))

    assert xio.core.post("/things/", json={"a": 1}).json() == {"ok": True}
    assert [seen["body"] for seen in core.requests] == ['{"a": 1}'] * 3
    assert waits == [2.0, 4.0]


def test_a_failed_read_is_sent_again(core: Server, waits: list[float]) -> None:
    """A 5xx on a GET is retried."""
    core.handler = answers((503, {}), (200, {"ok": True}))

    assert xio.core.get("/things/").json() == {"ok": True}
    assert len(waits) == 1


def test_a_failed_write_is_not_sent_again(core: Server, waits: list[float]) -> None:
    """A 5xx on a POST raises at once: the service may have acted on it."""
    core.handler = answers((500, {"detail": "boom"}))

    with pytest.raises(niquests.HTTPError):
        xio.core.post("/things/", json={})

    assert len(core.requests) == 1
    assert waits == []


def test_retrying_gives_up(core: Server, waits: list[float]) -> None:
    """After the configured number of attempts the failure raises."""
    core.handler = answers((503, {}))

    with pytest.raises(niquests.HTTPError, match="503"):
        xio.core.get("/things/")

    assert len(core.requests) == Config.attempts
    assert len(waits) == Config.attempts - 1


def test_the_wait_is_the_one_the_service_asks_for(core: Server, waits: list[float]) -> None:
    """Retry-After sets the wait, up to the configured limit."""
    core.headers = [("Retry-After", "7")]
    core.handler = answers((429, {}), (200, {}))
    xio.core.get("/things/")

    core.headers = [("Retry-After", "9999")]
    core.handler = answers((429, {}), (200, {}))
    xio.core.get("/things/")

    assert waits == [7.0, Config.retry_wait_limit_seconds]


@pytest.mark.usefixtures("waits")
def test_a_refused_token_is_renewed_once(core: Server, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 401 gets a new token and one more try, and the new token is kept for later requests."""
    monkeypatch.setattr(xio.client, "get_token", lambda _: "renewed")
    core.handler = lambda seen: (200, {}) if seen["authorization"] == "Bearer renewed" else (401, {})

    xio.core.get("/me")
    xio.core.get("/me")

    assert [seen["authorization"] for seen in core.requests] == ["Bearer stand-in", "Bearer renewed", "Bearer renewed"]


def test_a_token_refused_twice_raises(core: Server, monkeypatch: pytest.MonkeyPatch) -> None:
    """A 401 that a new token does not cure raises."""
    monkeypatch.setattr(xio.client, "get_token", lambda _: "renewed")
    core.handler = answers((401, {"detail": "Not you."}))

    with pytest.raises(niquests.HTTPError, match="401"):
        xio.core.get("/me")

    assert len(core.requests) == 2
