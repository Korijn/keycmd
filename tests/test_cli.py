import pytest

from keycmd import __version__
from keycmd.cli import cli, main


def test_cli_version(capfd):
    main(["--version"])
    assert capfd.readouterr().out.strip() == f"keycmd: v{__version__}"


def test_cli(capfd, shell_credentials, local_conf, userprofile, subprocess, shell):
    var = shell.env_var(local_conf.varname)

    with pytest.raises(SystemExit) as exc_info:
        main(["echo", var])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == shell_credentials.password


def test_cli_shell(shell_credentials, local_conf, userprofile, subprocess):
    """--shell spawns a subshell instead of running a command"""
    with pytest.raises(SystemExit) as exc_info:
        main(["--shell"])
    assert exc_info.value.args[0] == 0


def test_cli_verbose(capfd, shell_credentials, local_conf, userprofile, subprocess):
    with pytest.raises(SystemExit):
        main(["--verbose", "echo", "foo"])
    out = capfd.readouterr().out
    assert f"loading config file {local_conf.path}" in out
    assert f"as environment variable {local_conf.varname}" in out


def test_cli_missing_credential(capfd, local_conf, userprofile, subprocess, os_keyring):
    with pytest.raises(SystemExit) as exc_info:
        main(["echo", "foo"])
    assert exc_info.value.args[0] == 1
    assert "MISSING credential" in capfd.readouterr().err


def test_cli_missing_command(capfd, ch_tmpdir, userprofile):
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.args[0] == 1
    assert "missing command argument" in capfd.readouterr().err


def test_cli_invalid_conf(capfd, ch_tmpdir, userprofile):
    (ch_tmpdir / ".keycmd").write_text("[keys}", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        main(["echo", "foo"])
    assert exc_info.value.args[0] == 1
    assert "invalid TOML in" in capfd.readouterr().err


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
