from os import getpid
from subprocess import run
from sys import exit

from shellingham import detect_shell


def get_shell():
    """Use shellingham to detect the shell that invoked
    this Python process"""
    return detect_shell(getpid())


def run_shell(env=None):
    """Open an interactive shell for the user to interact
    with."""
    _, shell_path = get_shell()
    p = run(shell_path, shell=False, env=env)
    exit(p.returncode)


def run_cmd(cmd, env=None):
    """Run a one-off command in a shell."""
    shell_name, shell_path = get_shell()
    opt = "-c"
    if shell_name == "cmd":
        opt = "/C"
    p = run([shell_path, opt, *cmd], shell=False, env=env)
    exit(p.returncode)
