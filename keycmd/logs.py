from sys import exit


_verbose = False


def set_verbose():
    global _verbose
    _verbose = True


def log(msg):
    print(f"keycmd: {msg}")


def vlog(msg):
    if _verbose:
        print(f"keycmd: {msg}")


def error(msg):
    log(f"error: {msg}")
    exit(1)


def vwarn(msg):
    vlog(f"warning: {msg}")
