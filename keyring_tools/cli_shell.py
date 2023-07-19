from .conf import load_conf
from .creds import get_env
from .shell import run_shell


def main():
    conf = load_conf()
    env = get_env(conf)
    run_shell(env=env)
