"""Tests for the RichLog verbosity gating."""

from io import StringIO

from rich.console import Console

from xio.cli.output import OutputLevel, RichLog


def make_log(*, verbosity: int = 0, quiet: bool = False) -> RichLog:
    """Build a RichLog that writes to an in-memory, colour-free console."""
    log = RichLog(verbosity=verbosity, quiet=quiet)
    log.console = log.output = Console(file=StringIO(), width=500, force_terminal=False, no_color=True)
    return log


def output_of(log: RichLog) -> str:
    """Return everything written to the log's console."""
    stream = log.console.file
    assert isinstance(stream, StringIO)
    return stream.getvalue()


def test_default_threshold_is_normal() -> None:
    """With no flags the threshold sits at NORMAL."""
    assert make_log().threshold is OutputLevel.NORMAL


def test_quiet_threshold_is_warning() -> None:
    """Quiet mode raises the threshold to WARNING."""
    assert make_log(quiet=True).threshold is OutputLevel.WARNING


def test_verbosity_is_clamped() -> None:
    """Verbosity above the map's maximum clamps to DEBUG."""
    assert make_log(verbosity=99).threshold is OutputLevel.DEBUG


def test_default_shows_normal_hides_info_and_debug() -> None:
    """At the default level, NORMAL prints but INFO and DEBUG are suppressed."""
    log = make_log()
    log.debug("DEBUGMSG")
    log.info("INFOMSG")
    log.normal("NORMALMSG")

    out = output_of(log)
    assert "NORMALMSG" in out
    assert "INFOMSG" not in out
    assert "DEBUGMSG" not in out


def test_verbose_shows_info_hides_debug() -> None:
    """A single -v surfaces INFO but still hides DEBUG."""
    log = make_log(verbosity=1)
    log.info("INFOMSG")
    log.debug("DEBUGMSG")

    out = output_of(log)
    assert "INFOMSG" in out
    assert "DEBUGMSG" not in out


def test_very_verbose_shows_debug() -> None:
    """Two -v surface DEBUG."""
    log = make_log(verbosity=2)
    log.debug("DEBUGMSG")

    assert "DEBUGMSG" in output_of(log)


def test_quiet_shows_only_warning_and_error() -> None:
    """Quiet mode hides everything below WARNING."""
    log = make_log(quiet=True)
    log.debug("DEBUGMSG")
    log.info("INFOMSG")
    log.normal("NORMALMSG")
    log.success("SUCCESSMSG")
    log.warn("WARNMSG")  # noqa: G010 -- RichLog.warn is the intended API, not stdlib logging
    log.fail("ERRORMSG")

    out = output_of(log)
    assert "WARNMSG" in out
    assert "ERRORMSG" in out
    for hidden in ("DEBUGMSG", "INFOMSG", "NORMALMSG", "SUCCESSMSG"):
        assert hidden not in out


def test_raw_bypasses_threshold() -> None:
    """raw() prints regardless of the verbosity threshold."""
    log = make_log(quiet=True)
    log.raw("RAWMSG")

    assert "RAWMSG" in output_of(log)


def test_raw_prints_verbatim() -> None:
    """raw() neither wraps at the console width nor interprets markup or emoji codes."""
    log = make_log()
    log.output = log.console = Console(file=StringIO(), width=20, force_terminal=False, no_color=True)
    message = r'{"path": "C:\\[team]\\[bold]x[/bold]:smile:\\a-path-longer-than-the-console.exe"}'

    log.raw(message)

    assert output_of(log) == message + "\n"
