import argparse
import tomllib
from collections.abc import Sequence

from . import __version__
from .backend import detect_backend, reset_backend
from .conf import load_conf
from .creds import get_env
from .logs import error, log, set_verbose
from .shell import run_cmd, run_shell

EXAMPLES: str = """\
examples:
  keycmd npm install              run a command with the credentials exposed
  keycmd -- ruff --version        -- ends keycmd's own options
  keycmd 'echo $SECRET | wc -c'   quote it to use your shell's syntax
  keycmd --shell                  open a subshell with the credentials exposed
"""

cli: argparse.ArgumentParser = argparse.ArgumentParser(
    prog="keycmd",
    usage="%(prog)s [options] [--] [command ...]",
    epilog=EXAMPLES,
    formatter_class=argparse.RawDescriptionHelpFormatter,
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
cli.add_argument(
    "command",
    nargs=argparse.REMAINDER,
    help="command to run, as separate arguments or as one quoted string",
)


def end_of_options(command: Sequence[str]) -> list[str]:
    """The command to run, without the `--` that ends keycmd's own options

    Every tool that goes on to run another one takes `--`, so it is typed
    out of habit whether keycmd needs it or not. keycmd needs it only for a
    command whose first word starts with a dash, which argparse would
    otherwise read as an option of keycmd's; the rest of the command line
    is a REMAINDER, so `keycmd ruff --version` already reaches ruff intact.

    Since that REMAINDER is taken verbatim, the `--` is still sitting in it,
    where it would go on to be the first word of the command.
    """
    if command and command[0] == "--":
        return list(command[1:])
    return list(command)


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
    command = end_of_options(parsed.command)

    if parsed.shell:
        run_shell(env=env)
    elif command:
        run_cmd(command, env=env)
    else:
        error("missing command argument")
