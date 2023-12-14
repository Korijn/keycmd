import sys

_verbose = False


def set_verbose(verbose=True):
    global _verbose
    _verbose = verbose


def log(msg, err=False):
    msg = f"keycmd: {msg}"
    if err:
        print(msg, file=sys.stderr)
    else:
        print(msg)


def vlog(msg):
    if _verbose:
        print(f"keycmd: {msg}")


def error(msg):
    log(f"error: {msg}", err=True)
    sys.exit(1)


def vwarn(msg):
    vlog(f"warning: {msg}")
