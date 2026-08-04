import argparse
import tomllib
from collections.abc import Sequence

from . import __version__
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
