import sys
from typing import NoReturn

_verbose: bool = False


def set_verbose(verbose: bool = True) -> None:
    global _verbose
    _verbose = verbose


def log(msg: object, err: bool = False) -> None:
    line = f"keycmd: {msg}"
    if err:
        print(line, file=sys.stderr)
    else:
        print(line)


def vlog(msg: object) -> None:
    if _verbose:
        log(msg)


def vlog_pretty(prefix: str, value: object) -> None:
    """Log a value under --verbose, pretty printed over as many lines as it takes

    pprint costs more to import than everything else keycmd reaches for in
    the standard library, and only this function ever needs it, so it stays
    out of the import path until a verbose run asks for it.
    """
    if _verbose:
        from pprint import pformat

        log(f"{prefix}{pformat(value)}")


def error(msg: object, *hints: object) -> NoReturn:
    """Report why keycmd cannot go on, and exit

    The line that says what went wrong is rarely the line that says what
    to do about it, so an error can carry as many of the second kind as
    it takes. Both go to stderr, which is where keycmd writes anything
    that is not the output of the command it was asked to run.
    """
    log(f"error: {msg}", err=True)
    for hint in hints:
        log(f"hint: {hint}", err=True)
    sys.exit(1)


def vwarn(msg: object) -> None:
    vlog(f"warning: {msg}")
