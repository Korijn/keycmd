"""Shared fixtures for the keycmd test suite.

The suite runs on Windows, macOS and Linux. Everything that differs per
platform is expressed here, so the tests themselves stay platform agnostic.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import NamedTuple

import keyring
import pytest

import keycmd.conf
import keycmd.shell
import keycmd.wsl
from keycmd.logs import set_verbose
from keycmd.shell import IS_WINDOWS

# CI sets this so that a broken keyring setup fails the build loudly,
# instead of silently skipping every test that touches the keyring
REQUIRE_OS_KEYRING = os.environ.get("KEYCMD_REQUIRE_OS_KEYRING", "") not in {"", "0"}

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
    """Report which keyring backend the run picked up"""
    return f"keyring backend: {keyring.get_keyring()}"


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
