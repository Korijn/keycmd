"""Windows keycmd, called from a shell inside a WSL distribution

The end to end version of this lives in tests/test_wsl.py and needs a
windows machine with WSL installed. What is left here is everything that
can be decided without one: which process tree and working directory mean
keycmd was called from a distribution, the command lines it builds for
wsl.exe, and the WSLENV that carries the credentials across.
"""

import os
import sys
import types
from dataclasses import dataclass

import pytest

import keycmd.wsl
from keycmd.wsl import (
    OVERRIDE,
    ancestors,
    cmd_argv,
    from_wsl,
    image_name,
    in_distro,
    share_env,
    shell_argv,
)


@dataclass
class FakeProcess:
    """An entry of the windows process table, as shellingham reports it"""

    th32ProcessID: int  # noqa: N815 - the windows api spells it this way
    th32ParentProcessID: int  # noqa: N815
    szExeFile: bytes  # noqa: N815


@pytest.fixture
def windows(monkeypatch):
    """Pretend keycmd is the windows install, wherever the suite runs"""
    monkeypatch.setattr(keycmd.wsl, "IS_WINDOWS", True)
    monkeypatch.delenv(OVERRIDE, raising=False)


@pytest.fixture
def process_tree(monkeypatch):
    """Stand in for the process table shellingham reads on windows"""

    def install(*images):
        processes = []
        pid = os.getpid()
        for depth, image in enumerate(images):
            ppid = 10_000 + depth
            processes.append(FakeProcess(pid, ppid, image.encode("utf-8")))
            pid = ppid
        module = types.ModuleType("shellingham.nt")
        module._iter_processes = lambda: iter(processes)
        monkeypatch.setitem(sys.modules, "shellingham.nt", module)

    return install


@pytest.fixture
def no_process_tree(monkeypatch):
    """Make reading the process table fail, as it does off windows"""
    monkeypatch.setitem(sys.modules, "shellingham.nt", types.ModuleType("nope"))


@pytest.fixture
def cwd(monkeypatch):
    """Report a working directory without changing the real one"""

    def install(path):
        monkeypatch.setattr(keycmd.wsl.os, "getcwd", lambda: path)

    return install


def test_image_name():
    assert image_name("C:\\Windows\\System32\\cmd.exe") == "cmd"
    assert image_name("WSLHost.EXE") == "wslhost"
    assert image_name(b"bash") == "bash"


def test_ancestors(process_tree):
    process_tree("keycmd.exe", "wslhost.exe", "svchost.exe")
    assert ancestors() == ["keycmd", "wslhost", "svchost"]


def test_ancestors_stops_at_max_depth(process_tree):
    process_tree(*[f"parent{depth}.exe" for depth in range(20)])
    assert ancestors(max_depth=3) == ["parent0", "parent1", "parent2"]


def test_ancestors_without_process_table(no_process_tree):
    """An unreadable process table is reported as no answer, not an error"""
    assert ancestors() == []


def test_ancestors_verbose(capsys, no_process_tree, verbose):
    ancestors()
    assert "failed to read the windows process table" in capsys.readouterr().out


def test_from_wsl_needs_windows(process_tree, monkeypatch):
    """Inside a distribution keycmd is a posix process like any other"""
    monkeypatch.setattr(keycmd.wsl, "IS_WINDOWS", False)
    process_tree("keycmd.exe", "wsl.exe")
    assert from_wsl() is False


@pytest.mark.parametrize("host", ["wsl.exe", "wslhost.exe", "wslservice.exe"])
def test_from_wsl_by_process_tree(windows, process_tree, host):
    process_tree("keycmd.exe", host, "svchost.exe")
    assert from_wsl() is True


def test_from_wsl_windows_shell_wins(windows, process_tree):
    """A windows shell below the distribution is still a windows shell

    Which is what running a windows shell over the interop boundary, and
    calling keycmd from it, looks like.
    """
    process_tree("keycmd.exe", "cmd.exe", "wslhost.exe")
    assert from_wsl() is False


def test_from_wsl_by_working_directory(windows, no_process_tree, cwd):
    """The distribution's file system is only reachable over UNC"""
    cwd("\\\\wsl.localhost\\Ubuntu\\home\\someone\\project")
    assert from_wsl() is True
    cwd("\\\\WSL$\\Ubuntu\\home\\someone\\project")
    assert from_wsl() is True
    cwd("C:\\Users\\someone\\project")
    assert from_wsl() is False


def test_from_wsl_unknown(windows, process_tree, cwd):
    process_tree("keycmd.exe", "explorer.exe")
    cwd("C:\\Users\\someone\\project")
    assert from_wsl() is False


@pytest.mark.parametrize(
    ("override", "expected"),
    [("1", True), ("yes", True), ("0", False)],
)
def test_from_wsl_override(windows, process_tree, monkeypatch, override, expected):
    """The override has the last word, in either direction"""
    process_tree("keycmd.exe", "cmd.exe" if expected else "wsl.exe")
    monkeypatch.setenv(OVERRIDE, override)
    assert from_wsl() is expected


def test_from_wsl_override_verbose(capsys, windows, process_tree, monkeypatch, verbose):
    process_tree("keycmd.exe")
    monkeypatch.setenv(OVERRIDE, "1")
    from_wsl()
    assert f"{OVERRIDE}=1" in capsys.readouterr().out


def test_from_wsl_here():
    """Whatever this machine is, the answer is a boolean and not a crash"""
    assert from_wsl() in {True, False}


def test_in_distro(monkeypatch):
    assert in_distro() is False
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    assert in_distro() is True


def test_share_env(windows):
    env = {"FOO": "bar"}
    share_env(env, ["FOO", "BAZ"])
    assert env["WSLENV"] == "FOO:BAZ"


def test_share_env_from_distro(monkeypatch):
    """Windows commands run from inside a distribution need it too"""
    monkeypatch.setenv("WSL_INTEROP", "/run/WSL/1_interop")
    env = {}
    share_env(env, ["FOO"])
    assert env["WSLENV"] == "FOO"


def test_share_env_elsewhere():
    """On a machine without WSL there is no boundary to cross"""
    env = {}
    share_env(env, ["FOO"])
    assert env == {}


def test_share_env_keeps_existing(windows):
    """What the user shares survives, flags and all, and is not repeated"""
    env = {"WSLENV": "EXISTING/p:FOO"}
    share_env(env, ["FOO", "BAZ"])
    assert env["WSLENV"] == "EXISTING/p:FOO:BAZ"


def test_share_env_without_keys(windows):
    env = {}
    share_env(env, [])
    assert env == {}


def test_share_env_verbose(capsys, windows, verbose):
    share_env({}, ["FOO"])
    assert "sharing with WSL as WSLENV=FOO" in capsys.readouterr().out


def test_argv():
    assert shell_argv() == ["wsl.exe"]
    assert cmd_argv(["echo", "foo"]) == ["wsl.exe", "--", "echo", "foo"]
