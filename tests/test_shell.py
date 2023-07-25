from os import environ
from shutil import which

import pytest

from keycmd.shell import get_shell, run_shell, run_cmd


def test_get_shell():
    name, path = get_shell()
    assert which(path) is not None
    assert len(name)


def test_run_shell():
    with pytest.raises(SystemExit) as exc_info:
        run_shell()
    assert exc_info.value.args[0] == 0


def test_run_cmd(capfd):
    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", "foo"])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == "foo"

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["sadfdasfsdf"])
    assert exc_info.value.args[0] == 1


def test_run_cmd_env(capfd):
    env = environ.copy()
    var_value = "foobar"
    env["KEYCMD_TEST_FOOBAR"] = var_value

    name, _ = get_shell()
    if name == "cmd":
        var = r"%KEYCMD_TEST_FOOBAR%"
    elif name in {"pwsh", "powershell"}:
        var = "$env:KEYCMD_TEST_FOOBAR"
    else:
        var = "$KEYCMD_TEST_FOOBAR"

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", var], env=env)
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == var_value

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", var])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == var
