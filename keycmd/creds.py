import base64
from os import environ

import keyring

from .logs import error, vlog


def b64(value):
    """Convert a string to its base64 representation"""
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def get_env(conf):
    """Load credentials from the OS keyring according to user configuration"""
    env = environ.copy()
    loaded = {}
    for key, src in conf["keys"].items():
        password = keyring.get_password(src["credential"], src["username"])
        if password is None:
            error(
                f"MISSING credential {src['credential']}"
                f" with user {src['username']}"
                f" as it does not exist"
            )
        loaded[key] = password
        if src.get("b64"):
            password = b64(password)
        env[key] = password
        vlog(
            f"exposing credential {src['credential']}"
            f" with user {src['username']}"
            f" as environment variable {key} (b64: {src.get('b64', False)})"
        )
    for key, src in conf.get("aliases", {}).items():
        password = loaded.get(src["key"]])
        if password is None:
            error(f"MISSING alias key {src['key']}")
        if src.get("b64"):
            password = b64(password)
        env[key] = password
        vlog(
            f"aliasing {src['key']}"
            f" as environment variable {key} (b64: {src.get('b64', False)})"
        )
    return env
