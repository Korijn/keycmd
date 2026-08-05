import os
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path
from sys import exit
from typing import NoReturn

from shellingham import ShellDetectionFailure, detect_shell

from .logs import vlog, vlog_pretty, vwarn
from .wsl import cmd_argv, from_wsl, shell_argv

USE_SUBPROCESS: bool = False  # exposed for testing
IS_WINDOWS: bool = os.name == "nt"
IS_POSIX: bool = os.name == "posix"

# shells that take -c, but do not quote the way a posix shell does
POWERSHELL: frozenset[str] = frozenset({"powershell", "pwsh"})


def exec(args: list[str], env: Mapping[str, str] | None = None) -> NoReturn:
    if env is None:
        env = os.environ
    if USE_SUBPROCESS or IS_WINDOWS:
        # windows does not support process replacement
        # as well as posix systems do; the posix path below never spawns a
        # subprocess, so it does not pay to import one either
        from subprocess import run

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
    # shellingham walks the process table lazily, from inside a generator, so
    # a platform whose format it misjudges surfaces the failed read itself
    # rather than ShellDetectionFailure (sarugaku/shellingham#99). The system
    # default is a better answer than a traceback either way.
    except (ShellDetectionFailure, OSError) as err:
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


def quote(shell_name: str, arg: str) -> str:
    """Quote one argument so that a shell hands it on as a single word

    Everything that is not powershell is quoted the posix way, which
    covers every shell this is tested against and the great majority of
    what shellingham can detect. The exotic ones it also detects, csh and
    fish and nu among them, spell quoting their own way, and an argument
    that needs quoting may not survive one intact. An argument that needs
    no quoting is untouched, so the common command is unaffected either
    way.

    Quoting an argument is not always enough to deliver it. Windows
    powershell passes arguments to a native command the way it always
    has, which drops an embedded double quote and an empty argument no
    matter how they are written; powershell 7.3 fixed that, and pwsh
    carries both. cmd reaches a command through the windows command line,
    which cannot hold a newline at all.
    """
    quoted = shlex.quote(arg)
    if shell_name not in POWERSHELL or quoted == arg:
        # a posix shell, or an argument that needs no quoting in any shell
        return quoted
    # where a posix shell ends a single quoted string to spell a quote,
    # powershell doubles the quote and stays inside the string
    return "'" + arg.replace("'", "''") + "'"


def join_cmd(shell_name: str, cmd: Sequence[str]) -> str:
    """Turn a command into the single string a shell takes after -c

    One argument is a command line already. `keycmd 'echo $SECRET'` is the
    form the README recommends, and the shell is there precisely to
    interpret it, so it is handed over as typed.

    Several arguments are an argv vector, and joining them raw would feed
    their contents back to the shell to be split into words a second time.
    Quoting each one is what keeps `keycmd mytool 'hello world'` a single
    argument by the time mytool sees it.
    """
    if len(cmd) == 1:
        return cmd[0]
    quoted = [quote(shell_name, arg) for arg in cmd]
    if shell_name in POWERSHELL and quoted[0] != cmd[0]:
        # powershell reads a quoted command name as a string to print, and
        # needs the call operator to run it instead
        quoted.insert(0, "&")
    return " ".join(quoted)


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
            cmd = [join_cmd(shell_name, cmd)]
        full_command = [shell_path, opt, *cmd]
    vlog_pretty("running command: ", full_command)
    exec(full_command, env)
