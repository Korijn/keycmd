import argparse
import tomllib
from collections.abc import Sequence

from . import __version__
from .backend import detect_backend, reset_backend
from .conf import load_conf
from .creds import get_env
from .logs import error, log, set_verbose
from .shell import run_cmd, run_shell

cli: argparse.ArgumentParser = argparse.ArgumentParser(
    prog="keycmd",
)
cli.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=False,
    help="enable verbose output, useful for configuration debugging",
)
cli.add_argument(
    "--version", action="store_true", default=False, help="print version info"
)
cli.add_argument(
    "--detect-backend",
    action="store_true",
    default=False,
    help="search for the keyring backend now and remember it for later runs",
)
cli.add_argument(
    "--reset-backend",
    action="store_true",
    default=False,
    help="forget the remembered keyring backend, so the next run searches again",
)
cli.add_argument(
    "--shell",
    action="store_true",
    default=False,
    help="spawn a subshell instead of running a command",
)
cli.add_argument("command", nargs=argparse.REMAINDER, help="command to run")


def main(args: Sequence[str] | None = None) -> None:
    """CLI entrypoint"""
    parsed = cli.parse_args(args=args)

    if parsed.verbose:
        set_verbose()

    if parsed.version:
        log(f"v{__version__}")
        return

    # both are about the keyring itself, so neither has any use for the
    # configuration or for a command to run it against
    if parsed.detect_backend:
        detect_backend()
        return
    if parsed.reset_backend:
        reset_backend()
        return

    try:
        conf = load_conf()
    except tomllib.TOMLDecodeError as err:
        error(err)
    env = get_env(conf)

    if parsed.shell:
        run_shell(env=env)
    elif parsed.command:
        run_cmd(parsed.command, env=env)
    else:
        error("missing command argument")
