"""Noxfile."""

import shutil
from pathlib import Path

import nox

nox.options.default_venv_backend = "none"
nox.options.sessions = ["lints"]


CLEANABLE_TARGETS = [
    "./dist",
    "./build",
    "./.nox",
    "./.cache",
    "./coverage.xml",
    "./**/.mypy_cache",
    "./**/.pytest_cache",
    "./**/__pycache__",
    "./**/*.pyc",
    "./**/*.pyo",
]


@nox.session
def tests(session: nox.Session) -> None:
    """Run tests under coverage."""
    session.run("python", "-m", "coverage", "run", "-m", "pytest", "-v")


@nox.session
def lints(session: nox.Session) -> None:
    """Run lints."""
    session.run("prek", "run", "--all-files")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    session.run("mypy", "src/", "tests/")
    session.run("ty", "check", ".")


@nox.session
def clean(_: nox.Session) -> None:
    """Clean cache, .pyc, .pyo, and test/build artifact files from project."""
    for searchpath in CLEANABLE_TARGETS:
        for filepath in Path().glob(searchpath):
            if filepath.is_dir():
                shutil.rmtree(filepath)
            else:
                filepath.unlink()
