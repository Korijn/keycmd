import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from pprint import pformat
from subprocess import run
from sys import exit
from typing import NoReturn

from shellingham import ShellDetectionFailure, detect_shell

from .logs import vlog, vwarn
from .wsl import cmd_argv, from_wsl, shell_argv

USE_SUBPROCESS: bool = False  # exposed for testing
IS_WINDOWS: bool = os.name == "nt"
IS_POSIX: bool = os.name == "posix"


def exec(args: list[str], env: Mapping[str, str] | None = None) -> NoReturn:
    if env is None:
        env = os.environ
    if USE_SUBPROCESS or IS_WINDOWS:
        # windows does not support process replacement
        # as well as posix systems do
        p = run(args, shell=False, env=env)
        exit(p.returncode)
    # i know this looks like a bug
    # but it's a mandatory convention
    # to pass the process name as the first argument
    os.execvpe(args[0], args, env)


def get_shell() -> tuple[str, str]:
    """Use shellingham to detect the shell that invoked
    this Python process"""
    try:
        shell_name, shell_path = detect_shell(os.getpid())
    except ShellDetectionFailure as err:
        vwarn("failed to detect parent process shell, falling back to system default")
        if IS_POSIX:
            shell_path = os.environ["SHELL"]
        elif IS_WINDOWS:
            shell_path = os.environ["COMSPEC"]
        else:
            raise NotImplementedError(f"os {os.name} support not available") from err
        # shellingham reports names without their extension, and run_cmd
        # tells the shells apart by name, so COMSPEC has to lose its .exe
        shell_name = Path(shell_path).stem.lower()
    vlog(f"detected shell: {shell_path}")
    return shell_name, shell_path


def run_shell(env: Mapping[str, str] | None = None) -> NoReturn:
    """Open an interactive shell for the user to interact
    with."""
    if from_wsl():
        # the shell the user is typing in lives inside the distribution,
        # not on this side of the boundary
        vlog("spawning subshell in WSL")
        argv = shell_argv()
    else:
        shell_name, shell_path = get_shell()
        vlog(f"spawning subshell: {shell_name}")
        argv = [shell_path]
    exec(argv, env)


def run_cmd(cmd: Sequence[str], env: Mapping[str, str] | None = None) -> NoReturn:
    """Run a one-off command in a shell."""
    if from_wsl():
        full_command = cmd_argv(cmd)
    else:
        shell_name, shell_path = get_shell()
        if shell_name == "cmd":
            opt = "/C"
        else:
            opt = "-c"
            cmd = [" ".join(cmd)]
        full_command = [shell_path, opt, *cmd]
    vlog(f"running command: {pformat(full_command)}")
    exec(full_command, env)
