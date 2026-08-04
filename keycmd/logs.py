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
        print(f"keycmd: {msg}")


def error(msg: object) -> NoReturn:
    log(f"error: {msg}", err=True)
    sys.exit(1)


def vwarn(msg: object) -> None:
    vlog(f"warning: {msg}")
