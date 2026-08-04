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


def error(msg: object) -> NoReturn:
    log(f"error: {msg}", err=True)
    sys.exit(1)


def vwarn(msg: object) -> None:
    vlog(f"warning: {msg}")
