"""Run a script inside Xio's own environment."""

import runpy
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def run_script(script: Path, arguments: list[str]) -> None:
    """Run ``script`` as ``__main__`` with ``arguments``, as ``python script.py`` would."""
    saved_arguments, saved_path = sys.argv, sys.path[:]
    sys.argv = [str(script), *arguments]
    sys.path.insert(0, str(script.resolve().parent))
    try:
        runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv, sys.path[:] = saved_arguments, saved_path
