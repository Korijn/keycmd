from os import getpid
from subprocess import run
from sys import exit

from shellingham import detect_shell


def get_shell():
    _, shell_path = detect_shell(getpid())
    return shell_path


def run_shell(env=None):
    shell = get_shell()
    p = run(shell, shell=False, env=env)
    exit(p.returncode)


def run_cmd(cmd, env=None):
    p = run(cmd, shell=True, env=env)
    exit(p.returncode)
