"""Reaching the Windows credential manager from a WSL shell

The README tells WSL users to install keycmd on Windows and call it from
their WSL shell, so that keyring talks to the Windows credential manager
instead of a keyring daemon inside the distro. These tests walk that path
end to end: a credential in the credential manager, a shell inside WSL,
and the Windows install of keycmd in between.

Installing WSL is a CI job of its own, so they are opt in.
"""

import os
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


def wsl_bash(script):
    return wsl("bash", "-euo", "pipefail", "-c", script)


def wsl_path(path):
    """Translate a Windows path into the path WSL knows it by"""
    # wslpath takes forward slashes too, and unlike backslashes they
    # survive the trip through wsl.exe's command line
    windows_path = str(path).replace("\\", "/")
    p = wsl("wslpath", "-a", windows_path)
    assert p.returncode == 0, f"{windows_path}: {decode(p.stderr)}"
    return decode(p.stdout).strip()


@pytest.fixture(scope="session")
def keycmd_exe():
    """The Windows console script, as WSL users reach it through the PATH"""
    path = which("keycmd")
    assert path is not None, "the keycmd console script is not on PATH"
    return wsl_path(path)


def test_wsl_is_reachable():
    p = wsl_bash("uname -s")
    assert p.returncode == 0, decode(p.stderr)
    assert decode(p.stdout).strip() == "Linux"


def test_version_from_wsl(keycmd_exe):
    """The Windows install runs when it is invoked from a WSL shell"""
    p = wsl_bash(f"'{keycmd_exe}' --version")
    assert p.returncode == 0, decode(p.stderr)
    assert decode(p.stdout).strip().startswith("keycmd: v")


def test_credential_manager_from_wsl(
    keycmd_exe, ch_tmpdir, local_conf, shell_credentials
):
    """A credential stored on Windows reaches a command run from WSL"""
    var = local_conf.varname
    # one line, so the script survives the trip through wsl.exe intact:
    # the config is picked up from the working directory, which crosses the
    # boundary as a windows path, and the variable is spelled in both
    # dialects, so that the assertion does not depend on which shell keycmd
    # detects on the windows side of the boundary
    script = (
        f"cd '{wsl_path(ch_tmpdir)}'; "
        f"'{keycmd_exe}' --verbose echo '%{var}%' '$env:{var}'"
    )
    p = wsl_bash(script)
    output = f"{decode(p.stdout)}\n{decode(p.stderr)}"
    assert p.returncode == 0, output
    assert f"as environment variable {var}" in output
    assert shell_credentials.password in output
