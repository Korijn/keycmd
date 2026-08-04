import sys
from os import environ
from pprint import pformat
from shutil import which
from subprocess import run

import pytest
from shellingham import ShellDetectionFailure

import keycmd.shell
from keycmd.shell import IS_WINDOWS, get_shell, run_cmd, run_shell

VARNAME = "KEYCMD_TEST_FOOBAR"

posix_only = pytest.mark.skipif(
    IS_WINDOWS, reason="windows does not support process replacement"
)


@pytest.fixture
def undetectable_shell(monkeypatch):
    """Make shellingham fail, so get_shell falls back to the system default"""

    def detect_shell(pid):
        raise ShellDetectionFailure("nope")

    monkeypatch.setattr(keycmd.shell, "detect_shell", detect_shell)


def test_get_shell():
    name, path = get_shell()
    assert which(path) is not None
    assert len(name)


def test_get_shell_posix_fallback(monkeypatch, undetectable_shell):
    monkeypatch.setattr(keycmd.shell, "IS_POSIX", True)
    monkeypatch.setattr(keycmd.shell, "IS_WINDOWS", False)
    monkeypatch.setenv("SHELL", "/usr/bin/bash")
    assert get_shell() == ("bash", "/usr/bin/bash")


def test_get_shell_windows_fallback(monkeypatch, undetectable_shell):
    monkeypatch.setattr(keycmd.shell, "IS_POSIX", False)
    monkeypatch.setattr(keycmd.shell, "IS_WINDOWS", True)
    # a bare file name, so that the assertion also holds on posix, where
    # backslashes are not path separators
    monkeypatch.setenv("COMSPEC", "CMD.EXE")
    assert get_shell() == ("cmd.exe", "CMD.EXE")


def test_get_shell_unsupported_os(monkeypatch, undetectable_shell):
    monkeypatch.setattr(keycmd.shell, "IS_POSIX", False)
    monkeypatch.setattr(keycmd.shell, "IS_WINDOWS", False)
    with pytest.raises(NotImplementedError):
        get_shell()


def test_get_shell_fallback_warns(capsys, monkeypatch, undetectable_shell, verbose):
    monkeypatch.setenv("SHELL", "/usr/bin/bash")
    monkeypatch.setenv("COMSPEC", "CMD.EXE")
    get_shell()
    assert "warning: failed to detect parent process shell" in capsys.readouterr().out


def test_run_shell(subprocess):
    with pytest.raises(SystemExit) as exc_info:
        run_shell()
    assert exc_info.value.args[0] == 0


def test_run_cmd(capfd, subprocess, shell):
    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", "foo"])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == "foo"


def test_run_cmd_missing_command(subprocess, shell):
    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["sadfdasfsdf"])
    assert exc_info.value.args[0] in shell.command_not_found_statuses


def test_run_cmd_env(capfd, subprocess, shell):
    env = environ.copy()
    var_value = "foobar"
    env[VARNAME] = var_value
    var = shell.env_var(VARNAME)

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", var], env=env)
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == var_value

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", var])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == shell.unset_env_var(VARNAME)


def test_run_cmd_shell_invocation(capsys, subprocess, shell, verbose):
    with pytest.raises(SystemExit):
        run_cmd(["echo", "foo"])
    out = capsys.readouterr().out
    # cmd is the odd one out, it takes /C and keeps the arguments separate
    if shell.name == "cmd":
        expected = [shell.path, "/C", "echo", "foo"]
    else:
        expected = [shell.path, "-c", "echo foo"]
    # the command is logged through pformat, which wraps long shell paths
    # over several lines
    assert pformat(expected) in out


@pytest.mark.parametrize(
    ("shell_name", "expected"),
    [
        # cmd takes /C and keeps the arguments separate, every other
        # shell takes -c and a single command string
        ("cmd", ["/C", "echo", "foo", "bar"]),
        ("powershell", ["-c", "echo foo bar"]),
        ("bash", ["-c", "echo foo bar"]),
    ],
)
def test_run_cmd_invocation_per_shell(monkeypatch, shell_name, expected):
    """The command line is built for the shell keycmd was invoked from

    Covers the shells that are not installed on the current platform.
    """
    shell_path = f"/path/to/{shell_name}"
    monkeypatch.setattr(
        keycmd.shell, "detect_shell", lambda pid: (shell_name, shell_path)
    )
    invocations = []
    monkeypatch.setattr(
        keycmd.shell, "exec", lambda args, env=None: invocations.append((args, env))
    )
    run_cmd(["echo", "foo", "bar"], env={"FOO": "bar"})
    assert invocations == [([shell_path, *expected], {"FOO": "bar"})]


def test_exec_calls_execvpe(monkeypatch):
    """On posix the process is replaced, rather than spawning a subprocess"""
    monkeypatch.setattr(keycmd.shell, "USE_SUBPROCESS", False)
    monkeypatch.setattr(keycmd.shell, "IS_WINDOWS", False)
    calls = []
    monkeypatch.setattr(keycmd.shell.os, "execvpe", lambda *args: calls.append(args))
    keycmd.shell.exec(["echo", "foo"], env={"FOO": "bar"})
    assert calls == [("echo", ["echo", "foo"], {"FOO": "bar"})]


@posix_only
def test_exec_replaces_process():
    """The posix code path hands the process over to execvpe"""
    child = (
        "import sys;"
        "from keycmd.shell import exec;"
        "print('before', flush=True);"
        "exec([sys.executable, '-c',"
        " \"import os; print('after ' + os.environ['KEYCMD_TEST_EXEC'])\"],"
        " env={'KEYCMD_TEST_EXEC': 'foobar', 'PATH': os.environ['PATH']})"
    )
    p = run([sys.executable, "-c", "import os;" + child], capture_output=True)
    assert p.returncode == 0, p.stderr.decode()
    assert p.stdout.decode().split() == ["before", "after", "foobar"]


@posix_only
def test_exec_reports_exit_status():
    child = (
        "import sys;"
        "from keycmd.shell import exec;"
        "exec([sys.executable, '-c', 'raise SystemExit(3)'])"
    )
    p = run([sys.executable, "-c", child], capture_output=True)
    assert p.returncode == 3, p.stderr.decode()


@posix_only
def test_exec_inherits_environment():
    """Without an explicit env, the current environment is passed on"""
    child = (
        "import sys;"
        "from keycmd.shell import exec;"
        "exec([sys.executable, '-c',"
        " \"import os; print(os.environ['KEYCMD_TEST_EXEC'])\"])"
    )
    env = environ.copy()
    env["KEYCMD_TEST_EXEC"] = "inherited"
    p = run([sys.executable, "-c", child], capture_output=True, env=env)
    assert p.returncode == 0, p.stderr.decode()
    assert p.stdout.decode().strip() == "inherited"
