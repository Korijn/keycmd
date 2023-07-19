from .conf import load_conf
from .creds import get_env
from .shell import run_shell


def main():
    """Load user configuration, load credentials, spawn a shell"""
    conf = load_conf()
    env = get_env(conf)
    run_shell(env=env)
