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


def test_run_cmd():
    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["echo", "foo"])
    assert exc_info.value.args[0] == 0

    with pytest.raises(SystemExit) as exc_info:
        run_cmd(["sadfdasfsdf"])
    assert exc_info.value.args[0] == 1
