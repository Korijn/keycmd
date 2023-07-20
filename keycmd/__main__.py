import argparse

import tomli

from . import __version__
from .conf import load_conf
from .creds import get_env
from .logs import error, log, set_verbose
from .shell import run_cmd, run_shell


cli = argparse.ArgumentParser(
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
cli.add_argument("command", nargs="*", help="command to run")


def main():
    """CLI entrypoint"""
    args = cli.parse_args()

    if args.verbose:
        set_verbose()

    if args.version:
        log(f"v{__version__}")
        return

    try:
        conf = load_conf()
    except tomli.TOMLDecodeError as err:
        error(err)
    env = get_env(conf)

    if args.shell:
        run_shell(env=env)
    elif args.command:
        run_cmd(args.command, env=env)
    else:
        error("missing command argument")
