import sys
from subprocess import run

import pytest

from keycmd import __version__
from keycmd.backend import BACKEND_VAR, recall, remember
from keycmd.cli import cli, end_of_options, main

# modules that cost more to import than the rest of keycmd together, and
# that nothing needs until it is asked for: keyring only once a credential
# is looked up, pprint only under --verbose, subprocess only on the windows
# code path, which cannot replace its own process
LAZY_IMPORTS = ("keyring", "pprint", "subprocess")


def test_cli_version(capfd):
    main(["--version"])
    assert capfd.readouterr().out.strip() == f"keycmd: v{__version__}"


def test_cli(capfd, shell_credentials, local_conf, userprofile, subprocess, shell):
    # one argument, so that the shell keycmd hands the command line to is
    # the one that expands the variable
    var = shell.env_var(local_conf.varname)

    with pytest.raises(SystemExit) as exc_info:
        main([f"echo {var}"])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == shell_credentials.password


def test_cli_unquoted(
    capfd, shell_credentials, local_conf, userprofile, subprocess, shell
):
    """A command written out as separate arguments, the way it is typed

    The form the docs lead with, and the one that needs no shell of its
    own: the command reads the credential out of the environment keycmd
    handed it, rather than having a shell expand it first.
    """
    show = f"import os; print(os.environ[{local_conf.varname!r}])"

    with pytest.raises(SystemExit) as exc_info:
        main([sys.executable, "-c", show])
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


def test_cli_detect_backend(capfd, cache_home, monkeypatch, os_keyring):
    """Searching on purpose, and writing down what turns up"""
    monkeypatch.delenv(BACKEND_VAR, raising=False)
    main(["--detect-backend"])
    assert "remembered keyring backend" in capfd.readouterr().out
    assert recall() is not None


def test_cli_reset_backend(capfd, cache_home):
    """Forgetting on purpose, so that the next run searches again"""
    remember("keyring.backends.null.Keyring")
    main(["--reset-backend"])
    assert "forgot the remembered keyring backend" in capfd.readouterr().out
    assert recall() is None

    main(["--reset-backend"])
    assert "no keyring backend was remembered" in capfd.readouterr().out


def test_cli_backend_flags_need_no_command(cache_home):
    """Neither has any use for a command, or for a configuration to load"""
    for flag in ("--detect-backend", "--reset-backend"):
        args = cli.parse_args([flag])
        assert args.command == []


def test_cli_remembers_the_backend(
    capfd,
    cache_home,
    monkeypatch,
    shell_credentials,
    local_conf,
    userprofile,
    subprocess,
):
    """A run that had to search writes the answer down for the next one

    Which is the whole feature, seen from where the user stands: nothing
    to read, nothing to set, and the search paid for once.
    """
    # a machine that already names its backend has nothing to remember,
    # and this is about the machines that do not
    monkeypatch.delenv(BACKEND_VAR, raising=False)
    with pytest.raises(SystemExit) as exc_info:
        main(["echo", "foo"])
    assert exc_info.value.args[0] == 0
    # the command keeps the output to itself, and the note is on disk
    assert capfd.readouterr().out.strip() == "foo"
    assert recall() is not None


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


def test_cli_import_stays_lean():
    """Importing the cli does not pay for what a run may never use

    A fresh interpreter, because the test suite has imported keyring long
    before this point. Every one of these is a module level import away
    from landing back on the startup path of every invocation.
    """
    code = (
        "import sys, keycmd.cli;"
        f"print(' '.join(m for m in {LAZY_IMPORTS!r} if m in sys.modules))"
    )
    p = run([sys.executable, "-c", code], capture_output=True)
    assert p.returncode == 0, p.stderr.decode()
    assert p.stdout.decode().split() == []


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        # the habit every tool that runs another one teaches, which keycmd
        # would otherwise pass on as the first word of the command
        (["--", "npm", "install"], ["npm", "install"]),
        (["-v", "--", "npm", "install"], ["npm", "install"]),
        # what it is actually needed for: a command argparse would read as
        # an option of keycmd's
        (["--", "-l"], ["-l"]),
        (["--", "--version"], ["--version"]),
        # only the one that ends keycmd's options is keycmd's to remove
        (["npm", "install", "--", "--flag"], ["npm", "install", "--", "--flag"]),
        (["--", "--", "npm"], ["--", "npm"]),
        # nothing to run, which is reported as a missing command
        (["--"], []),
        ([], []),
    ],
    ids=repr,
)
def test_cli_end_of_options(argv, expected):
    """`--` ends keycmd's own options, and does not reach the command"""
    assert end_of_options(cli.parse_args(argv).command) == expected


def test_cli_end_of_options_runs_the_command(
    capfd, shell_credentials, local_conf, userprofile, subprocess, shell
):
    with pytest.raises(SystemExit) as exc_info:
        main(["--", "echo", "foo"])
    assert exc_info.value.args[0] == 0
    assert capfd.readouterr().out.strip() == "foo"


def test_cli_missing_command_after_end_of_options(capfd, ch_tmpdir, userprofile):
    with pytest.raises(SystemExit) as exc_info:
        main(["--"])
    assert exc_info.value.args[0] == 1
    assert "missing command argument" in capfd.readouterr().err


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
