"""Reaching a WSL distribution from the windows install of keycmd

The README tells WSL users to install keycmd on windows, so that keyring
talks to the windows credential manager instead of a keyring daemon inside
the distribution. That leaves keycmd a windows process with a windows idea
of a shell: asked for a subshell it opens cmd, and asked for a command it
runs it on windows, neither of which is what someone typing in a
distribution shell is after. `from_wsl` spots that situation, and
`shell_argv`/`cmd_argv` hand the work to wsl.exe instead.

The environment does not cross the boundary on its own. A windows process
started from a distribution does not inherit the linux environment, and a
distribution started from windows only receives the variables named in
WSLENV, which is why `share_env` writes it.
"""

import os
from collections.abc import Iterable, Sequence
from pathlib import PureWindowsPath

from .logs import vlog

# exposed for testing
IS_WINDOWS: bool = os.name == "nt"

# the windows api reports process names in the current code page, which
# python only knows as a codec on windows itself; not exposed for testing,
# so that a test can pretend to be windows without producing names no
# codec on this machine can read
NAME_ENCODING: str = "mbcs" if os.name == "nt" else "utf-8"

# the windows side of a distribution, which is what creates windows
# processes on its behalf
WSL_HOSTS: frozenset[str] = frozenset({"wsl", "wslhost", "wslservice"})

# shells that mean keycmd was called from windows after all, even when a
# distribution is somewhere further up the process tree
WINDOWS_SHELLS: frozenset[str] = frozenset({"cmd", "powershell", "pwsh"})

# where windows mounts the file systems of the distributions
WSL_ROOTS: tuple[str, ...] = ("\\\\wsl$\\", "\\\\wsl.localhost\\")

# set to 0 to keep keycmd on the windows side, to anything else to force it
# through wsl.exe, when the detection below gets it wrong
OVERRIDE: str = "KEYCMD_WSL"

WSL: str = "wsl.exe"


def image_name(image: str | bytes) -> str:
    """The name a process image is known by, without path or extension"""
    if isinstance(image, bytes):
        image = image.decode(NAME_ENCODING, "replace")
    return PureWindowsPath(image).stem.lower()


def ancestors(max_depth: int = 10) -> list[str]:
    """Image names of this process and its parents, nearest first

    Empty when the process table cannot be read, which is not fatal: the
    caller falls back on the working directory.
    """
    try:
        # keycmd already depends on shellingham for shell detection, and
        # this is the process table snapshot it walks to do it
        from shellingham.nt import _iter_processes

        tree = {
            proc.th32ProcessID: (proc.th32ParentProcessID, image_name(proc.szExeFile))
            for proc in _iter_processes()
        }
    except Exception as err:
        vlog(f"failed to read the windows process table: {err!r}")
        return []

    names = []
    pid = os.getpid()
    for _ in range(max_depth):
        entry = tree.get(pid)
        if entry is None:
            break
        pid, name = entry
        names.append(name)
    return names


def from_wsl() -> bool:
    """Was this windows process called from a shell inside WSL?"""
    if not IS_WINDOWS:
        # inside a distribution keycmd is a posix process like any other
        return False

    override = os.environ.get(OVERRIDE, "")
    if override:
        forced = override != "0"
        where = "from" if forced else "outside"
        vlog(f"{OVERRIDE}={override}, treating this as a call {where} WSL")
        return forced

    names = ancestors()
    if names:
        vlog(f"windows process tree: {' <- '.join(names)}")
    for name in names:
        if name in WSL_HOSTS:
            vlog(f"called from WSL, by way of {name}")
            return True
        if name in WINDOWS_SHELLS:
            vlog(f"called from the windows shell {name}")
            return False

    # a distribution's file system is reachable over UNC, so a windows
    # process called from one has its working directory there, unless the
    # distribution was sitting in a windows folder to begin with
    cwd = os.getcwd()
    if cwd.lower().startswith(WSL_ROOTS):
        vlog(f"called from WSL, working directory {cwd}")
        return True
    return False


def in_distro() -> bool:
    """Is this posix process running inside a WSL distribution?"""
    return "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ


def share_env(env: dict[str, str], names: Iterable[str]) -> None:
    """Let the named variables cross the boundary between WSL and windows

    Neither side inherits the other's environment; only the variables
    listed in WSLENV make the trip, in whichever direction is crossed.
    """
    if not (IS_WINDOWS or in_distro()):
        return
    shared = [entry for entry in env.get("WSLENV", "").split(":") if entry]
    listed = {entry.partition("/")[0] for entry in shared}
    shared += [name for name in dict.fromkeys(names) if name not in listed]
    if shared:
        env["WSLENV"] = ":".join(shared)
        vlog(f"sharing with WSL as WSLENV={env['WSLENV']}")


def shell_argv() -> list[str]:
    """Command line that opens an interactive shell in the distribution"""
    return [WSL]


def cmd_argv(cmd: Sequence[str]) -> list[str]:
    """Command line that runs a command in the distribution

    Without --exec, wsl.exe hands the command to the login shell of the
    distribution, which makes this the counterpart of the -c that run_cmd
    hands to a shell on either platform.
    """
    return [WSL, "--", *cmd]
