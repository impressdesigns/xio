# AGENTS.md

Operational guidance for AI agents working in Xio. Human contributor guide: [CONTRIBUTING.md](CONTRIBUTING.md).

## Project Overview

Xio is a developer's command-line helper for Core and Azure, installed on a Windows machine with `uv tool install`. It makes authenticated requests the way `gh api` does (`xio api`), runs scripts in its own environment with a signed-in client (`xio run`), signs in through the Azure CLI (`xio auth`) and prints a support report (`xio doctor`).

- **Stack:** Python 3.15, [uv](https://docs.astral.sh/uv/), Typer, niquests, jq.
- **Role:** A developer tool.
- **Distribution:** One package, `idi-xio`, importable as `xio`, published to PyPI when a GitHub release is published.

## Development & Verification Commands

```bash
# Sync dependencies
uv sync --locked

# Run linters (prek, ruff format + ruff check --fix, mypy, ty check) -- rewrites files
nox -s lints

# Run test suite
nox -s tests

# Non-mutating equivalents of what CI runs
uv run prek run --all-files
uv run ruff format --check .
uv run ruff check .
uv run mypy src/ tests/
uv run ty check .
uv run python -m coverage run -m pytest

# Try the CLI from the checkout
uv run xio --help
```

## Critical Invariants

- **Commands are thin.** A module under `xio/cli/` parses options and prints; what it does lives in a module beside `xio/cli/`, which a test calls directly.
- **Results go to standard output and everything else to standard error**, so a command's output pipes cleanly. A failure leaves standard output empty and exits non-zero.
- **`xio.tokens` is the only module that knows where a token comes from**, today the Azure CLI's signed-in account. Xio writes no token to disk.
- **A token goes only to its own service.** `services.resolve` refuses a URL whose host is not a listed service's.
- **`xio api` keeps `gh api`'s options and meanings.** Someone who knows one knows the other; an option that differs is a bug.
- **Pagination follows what the response says**: Core's `items`/`total`/`limit`/`offset` list envelope, or a next link on the service's own host.
- **`import xio` imports no HTTP stack and asks for no token.** `xio.core` and `xio.session(name)` sign in on first use, so a script that never calls a service never needs the Azure CLI.
- **Xio carries no SDK as a dependency.** A script that needs a package gets it with `uv tool install idi-xio --with <package>`, which keeps one environment.
- **A service is a base URL and a scope, nothing more.** Paths, entitlement codes and record shapes are never compiled in.
- **The suite never reaches the Azure CLI or the network.** `tests/conftest.py` removes both; a test that needs one puts a stand-in there.
- **`xio doctor` prints machine-readable JSON** through `RichLog.raw`, which prints verbatim (no markup, highlighting or wrapping), so the output still parses after being piped to a file.
- **The distribution is `idi-xio`; the module and the command are `xio`.** A different `xio` exists on public PyPI, so the distribution never takes that name.

## Where Things Live

```
src/xio/
├── services.py               # The APIs: name, base URL, token scope; path and URL resolution
├── tokens.py                 # Tokens and the signed-in account, from the Azure CLI
├── client.py                 # niquests sessions for a service, with or without a token
├── __init__.py               # What a script imports: core, session(name)
├── run.py                    # Running a script as __main__ in this environment
├── api.py                    # Building, sending, paging and rendering one request
├── doctor.py                 # Diagnostic report: tool, system, runtime, checks
└── cli/
    ├── app.py                # Typer root: -v/-q and the sub-commands
    ├── api.py                # xio api
    ├── auth.py               # xio auth login, status, token
    ├── doctor.py             # xio doctor
    ├── run.py                # xio run
    └── output.py             # RichLog: timestamped, level-filtered console output
tests/                        # One test module per source module
pyproject.toml                # Project, the dev group, ruff/mypy/ty/coverage/pytest settings
.python-version               # The Python CI and uv use
noxfile.py                    # lints, tests, clean
.github/workflows/            # ci.yaml, python-publish-pypi.yaml (publish on release)
```
