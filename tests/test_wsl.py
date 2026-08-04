"""Reaching the Windows credential manager from a WSL shell

The README tells WSL users to install keycmd on Windows and call it from
their WSL shell, so that keyring talks to the Windows credential manager
instead of a keyring daemon inside the distro. These tests walk that path
end to end: a credential in the credential manager, a shell inside WSL,
and the Windows install of keycmd in between.

Installing WSL is a CI job of its own, so they are opt in.
"""

import os
from pathlib import PureWindowsPath
from shutil import which
from subprocess import run

import pytest

RUN_WSL_TESTS = os.environ.get("KEYCMD_TEST_WSL", "") not in {"", "0"}

pytestmark = pytest.mark.skipif(
    not RUN_WSL_TESTS,
    reason="set KEYCMD_TEST_WSL=1 on a Windows machine with WSL installed",
)


def decode(raw):
    # the linux side writes utf-8, while wsl.exe reports its own errors in
    # utf-16, so keep going on undecodable bytes rather than swallow output
    return raw.decode("utf-8", errors="replace")


def wsl(*args):
    """Run a command in the default WSL distribution"""
    return run(["wsl.exe", "--", *args], capture_output=True)


def wsl_sh(script):
    """Run a shell script in the default WSL distribution

    Plain sh, since not every distribution ships bash.
    """
    return wsl("sh", "-eu", "-c", script)


def wsl_path(path):
    """Translate a Windows path into the path WSL knows it by

    Done here rather than with wslpath, which is not part of every
    distribution's root file system, and whose backslashes would not
    survive the trip through wsl.exe's command line anyway.
    """
    path = PureWindowsPath(path)
    drive = path.drive
    assert drive.endswith(":"), f"not an absolute windows path: {path}"
    rest = path.as_posix()[len(drive) :].lstrip("/")
    translated = f"/mnt/{drive[0].lower()}/{rest}"
    # quotes are stripped from wsl.exe's command line before the distribution
    # ever sees them, so a path with spaces cannot be passed through it
    assert " " not in translated, f"path with spaces: {translated}"
    return translated


@pytest.fixture(scope="session")
def keycmd_exe():
    """The Windows console script, as WSL users reach it through the PATH"""
    path = which("keycmd")
    assert path is not None, "the keycmd console script is not on PATH"
    return wsl_path(path)


def test_wsl_reads_windows_paths(tmp_path):
    """WSL is reachable, and it sees the Windows file system where expected"""
    marker = tmp_path / "marker"
    marker.write_text("hello from windows", encoding="utf-8")
    p = wsl_sh(f"cat {wsl_path(marker)}")
    assert p.returncode == 0, decode(p.stderr)
    assert decode(p.stdout).strip() == "hello from windows"


def test_version_from_wsl(keycmd_exe):
    """The Windows install runs when it is invoked from a WSL shell"""
    p = wsl_sh(f"{keycmd_exe} --version")
    assert p.returncode == 0, decode(p.stderr)
    assert decode(p.stdout).strip().startswith("keycmd: v")


def test_credential_manager_from_wsl(
    keycmd_exe, ch_tmpdir, local_conf, shell_credentials
):
    """A credential stored on Windows reaches a command run from WSL"""
    var = local_conf.varname
    # one line and free of quotes, so that the script survives the trip
    # through wsl.exe intact; the config is picked up from the working
    # directory, which crosses the boundary as a windows path, and printing
    # the environment with cmd works whichever shell keycmd ends up
    # detecting on the windows side, where %VAR% and $env:VAR each only
    # work in one of them
    script = f"cd {wsl_path(ch_tmpdir)}; {keycmd_exe} --verbose cmd /c set"
    p = wsl_sh(script)
    output = f"{decode(p.stdout)}\n{decode(p.stderr)}"
    assert p.returncode == 0, output
    assert f"as environment variable {var}" in output
    assert f"{var}={shell_credentials.password}" in output
