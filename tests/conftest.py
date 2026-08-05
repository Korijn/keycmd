"""Shared fixtures for the keycmd test suite.

The suite runs on Windows, macOS and Linux. Everything that differs per
platform is expressed here, so the tests themselves stay platform agnostic.
"""

import os
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PureWindowsPath
from shutil import which
from subprocess import run
from typing import NamedTuple

import keyring
import pytest

import keycmd.backend
import keycmd.conf
import keycmd.shell
import keycmd.wsl
from keycmd.logs import set_verbose
from keycmd.shell import IS_WINDOWS

# CI sets this so that a broken keyring setup fails the build loudly,
# instead of silently skipping every test that touches the keyring
REQUIRE_OS_KEYRING = os.environ.get("KEYCMD_REQUIRE_OS_KEYRING", "") not in {"", "0"}

# and this on the job that installs WSL, for the same reason: the tests
# that cross the interop boundary run wherever a distribution answers, so
# only the run that provisioned one can tell a skip from a broken setup
REQUIRE_WSL = os.environ.get("KEYCMD_REQUIRE_WSL", "") not in {"", "0"}

# shells to exercise, if installed
POSIX_SHELLS = ("sh", "bash", "zsh")
WINDOWS_SHELLS = ("cmd", "powershell")
# pwsh installs on every platform keycmd supports, and is the one shell
# taking -c that does not quote the way a posix shell does, so it is worth
# exercising wherever it turns up rather than on windows alone
ANY_PLATFORM_SHELLS = ("pwsh",)

# credential used by the keyring backed fixtures
KEY = "__keycmd_testß"
USERNAME = "usernameß"
PASSWORD = "passwordß"
# passwords that are echoed by a shell come back through the console
# encoding, which mangles non-ascii on windows
# TODO: figure out how to simulate pytest capfd encoding on CI
SHELL_PASSWORD = "password" if IS_WINDOWS else "passwordß"

# name of the environment variable the cli tests expose credentials as
VARNAME = "KEYCMD_TEST"


def pytest_report_header(config):
    """Report what this run picked up, all of which varies per machine

    Which shells a run covers, and whether it reached a WSL distribution,
    is otherwise only visible in the ids of the tests that failed, so a
    run where they all pass does not say whether a shell was exercised or
    simply absent.
    """
    shells = ", ".join(shell.name for shell in installed_shells())
    found = find_wsl()
    wsl = found.distro if isinstance(found, Wsl) else f"none, {found}"
    return [
        f"keyring backend: {keyring.get_keyring()}",
        f"shells exercised: {shells or 'none'}",
        f"WSL distribution: {wsl}",
    ]


@dataclass(frozen=True)
class Shell:
    """A shell to run keycmd's commands with, and its dialect"""

    name: str
    path: str

    def env_var(self, varname):
        """Reference to an environment variable in this shell's syntax"""
        if self.name == "cmd":
            return f"%{varname}%"
        if self.name in {"pwsh", "powershell"}:
            return f"$env:{varname}"
        return f"${varname}"

    def unset_env_var(self, varname):
        """What echoing an unset environment variable prints in this shell"""
        # cmd echoes the reference verbatim when the variable is not set
        if self.name == "cmd":
            return self.env_var(varname)
        return ""

    @property
    def command_not_found_statuses(self):
        """Exit statuses this shell may report for a command that is missing"""
        if self.name == "cmd":
            # cmd reports 9009, but has used 1 in the past
            return {1, 9009}
        if self.name in {"pwsh", "powershell"}:
            return {1}
        # posix shells standardize on 127
        return {127}

    def carries(self, args):
        """Can this shell hand these arguments on to a command unchanged?

        A shell keycmd hands a quoted command line to can carry anything,
        and the posix shells and pwsh do. The two windows shells reach a
        command through the windows command line instead, which is a
        narrower thing than an argv vector, and neither limit below is one
        that quoting on keycmd's side can lift.
        """
        if self.name == "cmd":
            # cmd is handed its arguments separately, and what quotes them
            # on the way is the windows runtime, which knows nothing of
            # cmd's own metacharacters: cmd parses those in any argument
            # the runtime saw no reason to quote, and expands %VAR% even
            # inside one that it did. A command line is also a line, so a
            # newline in an argument ends it early.
            return not any(set(arg) & set('&|<>()^%"\n') for arg in args)
        if self.name == "powershell":
            # windows powershell passes arguments to a native command the
            # way it always has, dropping an embedded double quote and an
            # empty argument outright. Powershell 7.3 fixed that, so pwsh
            # is held to the whole battery.
            return all(arg and '"' not in arg for arg in args)
        return True


def installed_shells():
    """The shells of this platform's candidate list that are installed"""
    candidates = (WINDOWS_SHELLS if IS_WINDOWS else POSIX_SHELLS) + ANY_PLATFORM_SHELLS
    found = []
    for name in candidates:
        path = which(name)
        if path is not None:
            found.append(Shell(name=name, path=path))
    return found


@pytest.fixture(params=installed_shells(), ids=lambda shell: shell.name)
def shell(request, monkeypatch):
    """Pretend keycmd was invoked from each installed shell in turn"""
    fake_shell = request.param

    def detect_shell(pid):
        return fake_shell.name, fake_shell.path

    monkeypatch.setattr(keycmd.shell, "detect_shell", detect_shell)
    return fake_shell


def decode(raw):
    """Text out of a distribution, whichever side of the boundary wrote it

    The linux side writes utf-8, while wsl.exe reports its own errors in
    utf-16; a NUL byte gives those away, since utf-8 output has none.
    Undecodable bytes are replaced rather than raised on, so that output
    that went wrong still reaches the assertion it explains.
    """
    if b"\x00" in raw:
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8", errors="replace")


class Output(NamedTuple):
    """What a command run inside a distribution had to say"""

    status: int
    stdout: str
    stderr: str

    @property
    def output(self):
        """Both streams, for the message of the assertion that failed"""
        return f"{self.stdout}\n{self.stderr}"


def wsl_run(*args):
    """Run a command in the default WSL distribution"""
    p = run(["wsl.exe", "--", *args], capture_output=True)
    return Output(p.returncode, decode(p.stdout), decode(p.stderr))


def wsl_sh(script):
    """Run a shell script in the default WSL distribution

    Plain sh, since not every distribution ships bash.
    """
    return wsl_run("sh", "-eu", "-c", script)


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


@dataclass(frozen=True)
class Wsl:
    """A distribution to run commands in, and the keycmd it can reach"""

    distro: str
    # the windows console script, as WSL users reach it through the PATH
    keycmd: str

    def sh(self, script):
        """Run a shell script inside the distribution"""
        return wsl_sh(script)

    def path(self, path):
        """The path this distribution knows a windows path by"""
        return wsl_path(path)


@cache
def find_wsl():
    """A WSL boundary this run can test across, or the reason there is none

    Windows keycmd called from a distribution is the half of the WSL setup
    that needs both sides of the boundary to be real, so it is tested
    wherever both are there and skipped, with the reason, where they are
    not. The answer is worked out once and reported in the header, since a
    run that skipped these silently looks exactly like a run without WSL.
    """
    if not IS_WINDOWS:
        return "keycmd only crosses the WSL boundary as a windows process"
    if which("wsl.exe") is None:
        return "wsl.exe is not installed"
    path = which("keycmd")
    if path is None:
        return "the keycmd console script is not on PATH"
    if " " in path:
        # wsl.exe strips the quotes that would hold it together, so a path
        # with spaces cannot be handed to the distribution at all
        return f"the keycmd console script is under a path with spaces: {path}"
    # a distribution that answers, rather than one that is merely
    # registered: wsl.exe is on PATH on windows whether or not there is
    # anything behind it, and docker's distributions run no shell
    found = wsl_sh("echo ${WSL_DISTRO_NAME:-default}")
    if found.status != 0 or not found.stdout.strip():
        said = " ".join(found.output.split())
        return f"no WSL distribution answered: {said or f'exit status {found.status}'}"
    return Wsl(distro=found.stdout.strip(), keycmd=wsl_path(path))


@pytest.fixture(scope="session")
def wsl():
    """A WSL distribution with the windows keycmd reachable from it"""
    found = find_wsl()
    if isinstance(found, str):
        msg = f"no WSL to test against: {found}"
        if REQUIRE_WSL:
            pytest.fail(msg)
        pytest.skip(msg)
    return found


@pytest.fixture(autouse=True)
def outside_wsl(monkeypatch):
    """Keep the suite off the WSL code path unless a test asks for it

    Windows keycmd called from a distribution hands the command to
    wsl.exe instead of to a windows shell, and shares the credentials
    through WSLENV. Neither belongs in a run of the rest of the suite,
    which should look the same on every platform; tests/test_wsl_interop.py
    drives that code path deliberately.
    """
    monkeypatch.setattr(keycmd.wsl, "IS_WINDOWS", False)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.delenv("WSL_INTEROP", raising=False)


@pytest.fixture(autouse=True)
def cache_home(tmp_path, monkeypatch):
    """Keep the remembered keyring backend out of the real cache folder

    keycmd writes down the backend it found so that later runs can skip
    the search, and a test run has no business reading or writing the
    note the machine it runs on is using. One folder per test, so that a
    test starts with nothing remembered unless it says otherwise.
    """
    home = tmp_path / ".cache"
    monkeypatch.setattr(keycmd.backend, "CACHE_HOME", home)
    return home


@pytest.fixture
def subprocess(monkeypatch):
    """Run commands in a subprocess instead of replacing this process"""
    monkeypatch.setattr(keycmd.shell, "USE_SUBPROCESS", True)


@pytest.fixture(autouse=True)
def reset_verbose():
    """Keep the global verbosity flag from leaking between tests"""
    yield
    set_verbose(False)


@pytest.fixture
def verbose(reset_verbose):
    set_verbose()


@pytest.fixture(scope="session")
def os_keyring():
    """Verify that this machine has a keyring that works unattended"""
    service = "__keycmd_test_probe"
    username = "probe"
    try:
        keyring.set_password(service, username, "probe")
        if keyring.get_password(service, username) != "probe":
            raise RuntimeError("password did not survive a round trip")
        keyring.delete_password(service, username)
    except Exception as err:
        msg = f"no OS keyring available that can be unlocked unattended: {err!r}"
        if REQUIRE_OS_KEYRING:
            pytest.fail(msg)
        pytest.skip(msg)
    return keyring.get_keyring()


class Credential(NamedTuple):
    key: str
    username: str
    password: str


def _store(password):
    keyring.set_password(KEY, USERNAME, password)
    yield Credential(KEY, USERNAME, password)
    keyring.delete_password(KEY, USERNAME)


@pytest.fixture
def credentials(os_keyring):
    """A credential in the OS keyring"""
    yield from _store(PASSWORD)


@pytest.fixture
def shell_credentials(os_keyring):
    """A credential in the OS keyring, safe to echo from a shell"""
    yield from _store(SHELL_PASSWORD)


@pytest.fixture
def ch_tmpdir(tmp_path):
    """Run in an empty directory, outside of any git repository"""
    cwd = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


@pytest.fixture
def userprofile(tmp_path, monkeypatch):
    """Point the user level config at an empty directory"""
    user_dir = tmp_path / ".user"
    user_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(keycmd.conf, "USERPROFILE", user_dir)
    return user_dir


class LocalConf(NamedTuple):
    path: Path
    varname: str


@pytest.fixture
def local_conf(ch_tmpdir):
    """A .keycmd exposing the fixture credential as an environment variable"""
    path = ch_tmpdir / ".keycmd"
    path.write_text(
        f"""[keys]
{VARNAME} = {{ credential = "{KEY}", username = "{USERNAME}" }}
""",
        encoding="utf-8",
    )
    return LocalConf(path, VARNAME)
