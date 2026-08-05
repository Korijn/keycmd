import json
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
    # without the extension, the way shellingham reports shell names, so
    # that run_cmd recognizes cmd and hands it /C
    assert get_shell() == ("cmd", "CMD.EXE")


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
    # one argument, the form the README recommends, so that the variable is
    # expanded by the shell keycmd hands the command line to
    cmd = [f"echo {shell.env_var(VARNAME)}"]

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(cmd, env=env)
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == var_value

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(cmd)
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


@pytest.mark.parametrize(
    ("shell_name", "cmd", "expected"),
    [
        # one argument is a command line already, and is handed over as
        # typed, so that the shell interprets it
        ("bash", ["echo $FOO bar"], ["-c", "echo $FOO bar"]),
        ("powershell", ["echo $env:FOO"], ["-c", "echo $env:FOO"]),
        # several arguments are an argv vector, and keep their word
        # boundaries rather than being split a second time by the shell
        ("bash", ["mytool", "hello world"], ["-c", "mytool 'hello world'"]),
        ("bash", ["mytool", "$FOO"], ["-c", "mytool '$FOO'"]),
        ("bash", ["mytool", "it's"], ["-c", """mytool 'it'"'"'s'"""]),
        # powershell spells an embedded quote by doubling it
        ("powershell", ["mytool", "hello world"], ["-c", "mytool 'hello world'"]),
        ("powershell", ["mytool", "it's"], ["-c", "mytool 'it''s'"]),
        # and needs the call operator once the command name is quoted
        ("powershell", ["my tool", "arg"], ["-c", "& 'my tool' arg"]),
        # nothing to quote, so nothing changes
        ("bash", ["echo", "foo"], ["-c", "echo foo"]),
        # cmd keeps the arguments separate and never joins them at all
        ("cmd", ["mytool", "hello world"], ["/C", "mytool", "hello world"]),
    ],
)
def test_run_cmd_quoting(monkeypatch, shell_name, cmd, expected):
    """Arguments survive the trip through the shell as the words they were

    Covers the shells that are not installed on the current platform.
    """
    shell_path = f"/path/to/{shell_name}"
    monkeypatch.setattr(
        keycmd.shell, "detect_shell", lambda pid: (shell_name, shell_path)
    )
    invocations = []
    monkeypatch.setattr(
        keycmd.shell, "exec", lambda args, env=None: invocations.append(args)
    )
    run_cmd(cmd)
    assert invocations == [[shell_path, *expected]]


# every way a shell might be tempted to read an argument as something
# other than the word it is: quoting of its own, expansions, globs, command
# separators, redirections, and whitespace it would otherwise split on
ROUNDTRIP_ARGS = [
    ["hello world"],
    ["it's"],
    ['say "hi"'],
    ["mixed 'single' and \"double\""],
    [r"C:\path\to", "back\\slash"],
    ["$HOME", "${X}", "$(id)"],
    ["`id`"],
    ["*", "?", "[a-z]"],
    ["a;b", "a&b", "a|b"],
    ["a\nb"],
    ["a\tb"],
    [""],
    ["a!b"],
    ["~", "~root"],
    ["ünïcødeß"],
    [">out", "<in", "2>&1"],
    ["(a)", "{b}"],
    ["#c", "a#b"],
    ["a b'c\"d\\e$f`g;h|i*j"],
]


@pytest.mark.parametrize("args", ROUNDTRIP_ARGS, ids=lambda args: repr(args))
def test_run_cmd_preserves_argv(capfd, subprocess, shell, args):
    """Arguments arrive as the words they were, whatever is in them

    Through python rather than echo, because it is the argv the command
    receives that is under test, and every platform running this suite has
    an interpreter that can report it back.
    """
    if not shell.carries(args):
        pytest.skip(f"{shell.name} parses these itself before the command sees them")

    show = "import sys, json; print(json.dumps(sys.argv[1:]))"
    with pytest.raises(SystemExit) as exc_info:
        run_cmd([sys.executable, "-c", show, *args])
    assert exc_info.value.args[0] == 0
    assert json.loads(capfd.readouterr().out) == args


@pytest.fixture
def called_from_wsl(monkeypatch):
    """Pretend the windows install was called from a distribution shell"""
    monkeypatch.setattr(keycmd.shell, "from_wsl", lambda: True)
    invocations = []
    monkeypatch.setattr(
        keycmd.shell, "exec", lambda args, env=None: invocations.append((args, env))
    )
    return invocations


def test_run_shell_in_wsl(called_from_wsl):
    """--shell opens a shell in the distribution, not a windows shell"""
    run_shell(env={"FOO": "bar"})
    assert called_from_wsl == [(["wsl.exe"], {"FOO": "bar"})]


def test_run_cmd_in_wsl(called_from_wsl):
    """The command runs in the distribution, where the user typed it"""
    run_cmd(["echo", "foo"], env={"FOO": "bar"})
    assert called_from_wsl == [(["wsl.exe", "--", "echo", "foo"], {"FOO": "bar"})]


def test_run_cmd_in_wsl_verbose(capsys, called_from_wsl, verbose):
    run_cmd(["echo", "foo"])
    assert pformat(["wsl.exe", "--", "echo", "foo"]) in capsys.readouterr().out


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
