"""Tests for xio.api and the api command."""

import json
from typing import TYPE_CHECKING, Any

import pytest
from typer.testing import CliRunner

from tests.stand_in import SERVICE, Reply, Server, paged
from xio import api
from xio.cli.app import app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_typed_fields_read_json_scalars_and_leave_the_rest_as_text() -> None:
    """-F reads true, false, null and numbers; anything else stays the string typed."""
    assert api.parse_field("a=true", typed=True) == ("a", True)
    assert api.parse_field("a=null", typed=True) == ("a", None)
    assert api.parse_field("a=12", typed=True) == ("a", 12)
    assert api.parse_field("a=1.5", typed=True) == ("a", 1.5)
    assert api.parse_field("a=hello", typed=True) == ("a", "hello")
    assert api.parse_field('a={"b": 1}', typed=True) == ("a", '{"b": 1}')
    assert api.parse_field("a=b=c", typed=True) == ("a", "b=c")


def test_raw_fields_are_always_strings() -> None:
    """-f never converts."""
    assert api.parse_field("a=true", typed=False) == ("a", "true")
    assert api.parse_field("a=12", typed=False) == ("a", "12")


def test_a_typed_field_reads_a_file(tmp_path: Path) -> None:
    """-F key=@file sends the file's text."""
    note = tmp_path / "note.txt"
    note.write_text("from a file")

    assert api.parse_field(f"a=@{note}", typed=True) == ("a", "from a file")


def test_a_field_without_a_key_or_value_is_refused() -> None:
    """A field that is not key=value is a usage error."""
    with pytest.raises(api.UsageError):
        api.parse_field("novalue", typed=False)
    with pytest.raises(api.UsageError):
        api.parse_field("=x", typed=False)


def test_get_is_the_default_and_fields_become_the_query(server: Server) -> None:
    """With nothing to send the method is GET; with -X GET, fields are the query string."""
    result = runner.invoke(app, ["api", "/things/", "-X", "GET", "-f", "search=red shirt", "-F", "limit=5"])

    assert result.exit_code == 0
    seen = server.requests[0]
    assert seen["method"] == "GET"
    assert seen["path"] == "/things/"
    assert seen["query"] == {"search": "red shirt", "limit": "5"}
    assert seen["body"] == ""
    assert seen["authorization"] == "Bearer stand-in"


def test_fields_without_a_method_post_a_json_body(server: Server) -> None:
    """Fields with no -X are POSTed as one JSON object, typed values keeping their types."""
    result = runner.invoke(app, ["api", "/things/", "-f", "name=Widget", "-F", "count=3", "-F", "active=true"])

    assert result.exit_code == 0
    seen = server.requests[0]
    assert seen["method"] == "POST"
    assert json.loads(seen["body"]) == {"name": "Widget", "count": 3, "active": True}


def test_input_sends_the_file_as_the_body(server: Server, tmp_path: Path) -> None:
    """--input sends the file verbatim as JSON, and fields move to the query string."""
    payload = tmp_path / "payload.json"
    payload.write_text('{"tasks": [1, 2]}')

    result = runner.invoke(app, ["api", "/tasks/bulk", "--input", str(payload), "-f", "dry_run=1"])

    assert result.exit_code == 0
    seen = server.requests[0]
    assert seen["method"] == "POST"
    assert seen["body"] == '{"tasks": [1, 2]}'
    assert seen["content_type"] == "application/json"
    assert seen["query"] == {"dry_run": "1"}


def test_input_from_stdin(server: Server) -> None:
    """--input - reads the body from standard input."""
    result = runner.invoke(app, ["api", "/things/1", "-X", "PATCH", "--input", "-"], input='{"name": "x"}')

    assert result.exit_code == 0
    assert server.requests[0]["method"] == "PATCH"
    assert server.requests[0]["body"] == '{"name": "x"}'


def test_headers_are_sent(server: Server) -> None:
    """-H adds a request header."""
    runner.invoke(app, ["api", "/me", "-H", "X-Test: yes"])

    assert server.requests[0]["x_test"] == "yes"


def test_jq_prints_strings_bare_and_the_rest_as_json(server: Server) -> None:
    """--jq prints one result per line: a string as it is, anything else as JSON."""
    server.handler = lambda _: (200, {"name": "Widget", "sizes": [1, 2], "owner": {"id": 7}})

    result = runner.invoke(app, ["api", "/things/1", "--jq", ".name, .sizes, .owner"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["Widget", "[1, 2]", '{"id": 7}']


def test_a_bad_jq_expression_fails_before_any_request(server: Server) -> None:
    """A jq syntax error is reported without calling the service."""
    result = runner.invoke(app, ["api", "/me", "--jq", ".["])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert server.requests == []


def test_without_jq_the_body_is_printed_as_sent(server: Server) -> None:
    """Piped output is the response body, byte for byte."""
    server.handler = lambda _: (200, b'{"a":1,\n "b":2}')

    result = runner.invoke(app, ["api", "/me"])

    assert result.stdout == '{"a":1,\n "b":2}\n'


def test_include_prints_the_status_and_headers_first(server: Server) -> None:
    """--include puts the status line and headers ahead of the body."""
    result = runner.invoke(app, ["api", "/me", "--include", "--jq", ".path"])

    assert len(server.requests) == 1
    lines = result.stdout.splitlines()
    assert lines[0].startswith("HTTP 200")
    assert "X-Served-By: stand-in" in lines
    assert lines[-1] == "/me"


def test_an_error_response_prints_its_body_and_exits_non_zero(server: Server) -> None:
    """A refused request still shows what the service said, and the command fails."""
    server.handler = lambda _: (403, {"detail": "Insufficient permissions"})

    result = runner.invoke(app, ["api", "/secret", "--jq", ".never"])

    assert result.exit_code == 1
    assert json.loads(result.stdout) == {"detail": "Insufficient permissions"}
    assert "403" in result.stderr


def test_paginate_walks_the_list_envelope(server: Server) -> None:
    """--paginate follows offset until total is reached, keeping the caller's other parameters."""
    server.handler = paged(list(range(7)), page_size=3)

    result = runner.invoke(app, ["api", "/things/", "-X", "GET", "-f", "limit=3", "--paginate", "--jq", ".items[]"])

    assert result.exit_code == 0
    assert [int(line) for line in result.stdout.splitlines()] == list(range(7))
    assert [seen["query"].get("offset", "0") for seen in server.requests] == ["0", "3", "6"]
    assert all(seen["query"]["limit"] == "3" for seen in server.requests)


def test_without_paginate_only_the_first_page_is_fetched(server: Server) -> None:
    """A list is one request unless --paginate is given."""
    server.handler = paged(list(range(7)), page_size=3)

    runner.invoke(app, ["api", "/things/"])

    assert len(server.requests) == 1


def test_paginate_stops_on_an_empty_page(server: Server) -> None:
    """A page with no items ends the walk even when total claims more."""
    server.handler = lambda seen: (
        200,
        {"items": [], "total": 99, "limit": 3, "offset": int(seen["query"].get("offset", 0))},
    )

    runner.invoke(app, ["api", "/things/", "--paginate"])

    assert len(server.requests) == 1


def test_paginate_follows_a_next_link(server: Server) -> None:
    """A body with a next link on the same host is followed."""

    def handler(seen: dict[str, Any]) -> Reply:
        if seen["path"] == "/v1.0/users":
            return 200, {"value": [1], "@odata.nextLink": f"{SERVICE.base_url}/v1.0/users/next"}
        return 200, {"value": [2]}

    server.handler = handler

    result = runner.invoke(app, ["api", "/v1.0/users", "--paginate", "--jq", ".value[]"])

    assert result.stdout.splitlines() == ["1", "2"]


def test_a_next_link_to_another_host_is_not_followed(server: Server) -> None:
    """A next link pointing off the service ends the command; the token never goes there."""
    server.handler = lambda _: (200, {"value": [1], "nextLink": "https://elsewhere.test/next"})

    result = runner.invoke(app, ["api", "/v1.0/users", "--paginate"])

    assert result.exit_code == 1
    assert len(server.requests) == 1


def test_a_url_on_a_foreign_host_is_refused_before_any_token() -> None:
    """A full URL that is no service's is refused without asking for a token."""
    result = runner.invoke(app, ["api", "https://example.com/me"])

    assert result.exit_code == 1
    assert result.stdout == ""
