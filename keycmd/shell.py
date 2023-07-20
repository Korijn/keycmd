import os
from pathlib import Path
from pprint import pformat
from subprocess import run
from sys import exit

from shellingham import detect_shell, ShellDetectionFailure

from .logs import vlog, vwarn


def get_shell():
    """Use shellingham to detect the shell that invoked
    this Python process"""
    try:
        shell_name, shell_path = detect_shell(os.getpid())
    except ShellDetectionFailure:
        vwarn("failed to detect parent process shell, falling back to system default")
        if os.name == "posix":
            shell_path = os.environ["SHELL"]
        elif os.name == "nt":
            shell_path = os.environ["COMSPEC"]
        else:
            raise NotImplementedError(f"os {os.name} support not available")
        shell_name = Path(shell_path).name.lower()
    vlog(f"detected shell: {shell_path}")
    return shell_name, shell_path


def run_shell(env=None):
    """Open an interactive shell for the user to interact
    with."""
    _, shell_path = get_shell()
    vlog("spawning subshell")
    p = run(shell_path, shell=False, env=env)
    exit(p.returncode)


def run_cmd(cmd, env=None):
    """Run a one-off command in a shell."""
    shell_name, shell_path = get_shell()
    opt = "-c"
    if shell_name == "cmd":
        opt = "/C"
    full_command = [shell_path, opt, *cmd]
    vlog(f"running command: {pformat(full_command)}")
    p = run(full_command, shell=False, env=env)
    exit(p.returncode)
