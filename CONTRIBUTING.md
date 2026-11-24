# Contributing

Python 3.15 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --locked
```

## Checks

`nox` runs the linters (and rewrites files: `ruff format`, `ruff check --fix`); `nox -s tests`
runs the suite. Individually, as CI runs them:

```bash
uv run prek run --all-files
uv run ruff format --check .
uv run ruff check .
uv run mypy src/ tests/
uv run ty check .
uv run python -m coverage run -m pytest
```

## Trying a change

```bash
uv tool install --editable .
```

installs the `xio` command from the checkout, so an edit is live without a release.

## Releasing

Bump `version` in `pyproject.toml`, then publish a GitHub release:
`python-publish-pypi.yaml` builds the package and uploads it to PyPI.
