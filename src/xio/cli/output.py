"""Rich console output manager."""

from datetime import datetime
from enum import IntEnum

from rich.console import Console
from rich.text import Text


class OutputLevel(IntEnum):
    """Output verbosity levels, ordered from least to most severe."""

    DEBUG = 0
    INFO = 1
    NORMAL = 2
    SUCCESS = 3
    WARNING = 4
    ERROR = 5


STYLES = {
    OutputLevel.DEBUG: "grey50",
    OutputLevel.INFO: "default",
    OutputLevel.NORMAL: "default",
    OutputLevel.SUCCESS: "bold green",
    OutputLevel.WARNING: "bold yellow",
    OutputLevel.ERROR: "bold red",
}

VERBOSITY_MAP = {
    0: OutputLevel.NORMAL,
    1: OutputLevel.INFO,
    2: OutputLevel.DEBUG,
}


def _get_log_timestamp() -> str:
    """Get the current timestamp for logging purposes."""
    return datetime.now().isoformat()  # noqa: DTZ005 -- shown to the person at the terminal, in their local time


class RichLog:
    """Rich console output manager: messages to standard error, results to standard output."""

    QUIET_LEVEL = OutputLevel.WARNING  # only warning + error

    def __init__(self, verbosity: int = 0, *, quiet: bool = False) -> None:
        self.console = Console(stderr=True)
        self.output = Console()

        if quiet:
            self.threshold = self.QUIET_LEVEL
        else:
            clamped = min(verbosity, max(VERBOSITY_MAP))
            self.threshold = VERBOSITY_MAP[clamped]

    def display(self, message: str, level: OutputLevel) -> None:
        """Print message if it passes verbosity threshold."""
        if level < self.threshold:
            return

        text = Text(
            f"{_get_log_timestamp()} [{level.name}] {message}",
            style=STYLES[level],
        )
        self.console.print(text)

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self.display(message, OutputLevel.DEBUG)

    def info(self, message: str) -> None:
        """Log an info message."""
        self.display(message, OutputLevel.INFO)

    def normal(self, message: str) -> None:
        """Log a normal message."""
        self.display(message, OutputLevel.NORMAL)

    def success(self, message: str) -> None:
        """Log a success message."""
        self.display(message, OutputLevel.SUCCESS)

    def warn(self, message: str) -> None:
        """Log a warning message."""
        self.display(message, OutputLevel.WARNING)

    def fail(self, message: str) -> None:
        """Log an error message."""
        self.display(message, OutputLevel.ERROR)

    def raw(self, message: str, *, style: str | None = None) -> None:
        """Print a result to standard output without timestamps, prefixes, or verbosity filtering.

        The message is printed verbatim: no markup, highlighting or emoji codes,
        and no wrapping at the console width, so machine-readable output such as
        the doctor's JSON survives being piped to a file.
        """
        self.output.print(message, style=style, markup=False, highlight=False, emoji=False, soft_wrap=True)
