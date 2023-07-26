import os
from pathlib import Path
from subprocess import run
from functools import cache

import pytest
import keyring

import keycmd.conf
from keycmd.shell import get_shell
from keycmd import __version__
from keycmd.cli import main, cli


varname = "KEYCMD_TEST"
key = "__keycmd_testß"
username = "usernameß"
# TODO: figure out how to simulate pytest capfd encoding on CI
password = "password"


@pytest.fixture
def credentials():
    keyring.set_password(key, username, password)
    yield
    keyring.delete_password(key, username)


@pytest.fixture
def ch_tmpdir(tmpdir):
    cwd = Path.cwd()
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(cwd)


@pytest.fixture
def userprofile(tmpdir, monkeypatch):
    user_dir = Path(tmpdir) / ".user"
    user_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(keycmd.conf, "USERPROFILE", user_dir)
    yield user_dir


@pytest.fixture
def local_conf(ch_tmpdir):
    Path(".keycmd").write_text(
        """[keys]
{varname} = {{ credential = "{key}", username = "{username}" }}
""".format(
            varname=varname,
            key=key,
            username=username,
        ),
        encoding="utf-8",
    )


@cache
def get_encoding_stdin():
    shell_name, _ = get_shell()
    opt = "-c"
    if shell_name == "cmd":
        opt = "/C"
    p = run(
        [shell_name, opt, "python", "-c", "import sys; print(sys.stdin.encoding)"],
        shell=False,
        capture_output=True,
        check=True,
    )
    return p.stdout.decode("utf-8").strip()


def test_cli_version(capfd):
    main(["--version"])
    assert capfd.readouterr().out.strip() == f"keycmd: v{__version__}"


def test_cli(capfd, ch_tmpdir, credentials, local_conf, userprofile):
    name, _ = get_shell()
    if name == "cmd":
        var = f"%{varname}%"
    elif name in {"pwsh", "powershell"}:
        var = f"$env:{varname}"
    else:
        var = f"${varname}"

    with pytest.raises(SystemExit):
        main(["echo", var])
    assert capfd.readouterr().out.strip() == password


def test_cli_missing_credential(capfd, ch_tmpdir, local_conf, userprofile):
    with pytest.raises(SystemExit) as exc_info:
        main(["echo", "foo"])
    assert exc_info.value.args[0] == 1


def test_cli_extra_args():
    command = ["echo", "foo", "-f", "bla", "--something"]
    args = cli.parse_args(command)
    assert args.command == command

    command = ["echo", "foo", "-f", "bla", "--version", "--something"]
    args = cli.parse_args(command)
    assert args.command == command

    command = ["--version", "echo", "foo", "-f", "bla", "--version", "--something"]
    args = cli.parse_args(command)
    assert args.command == command[1:]
    assert args.version is True
