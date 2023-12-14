import base64
from os import environ

import keyring

from .logs import error, vlog


def b64(value):
    """Convert a string to its base64 representation"""
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def expose(env, key, credential, username, password, apply_b64, format_string):
    if format_string:
        password = format_string.format(
            credential=credential,
            username=username,
            password=password,
        )
    if apply_b64:
        password = b64(password)
    env[key] = password


def get_env(conf):
    """Load credentials from the OS keyring according to user configuration"""
    env = environ.copy()

    key_data = {}
    for key, src in conf["keys"].items():
        password = keyring.get_password(src["credential"], src["username"])
        if password is None:
            error(
                f"MISSING credential {src['credential']}"
                f" with user {src['username']}"
                f" as it does not exist"
            )
        apply_b64 = src.get("b64", False)
        format_string = src.get("format")
        key_data[key] = (
            src["credential"],
            src["username"],
            password,
            apply_b64,
            format_string,
        )
        expose(env, key, *key_data[key])
        vlog(
            f"exposing credential {src['credential']}"
            f" with user {src['username']}"
            f" as environment variable {key}"
            f" (b64: {apply_b64}, format: {format_string})"
        )

    for alias, src in conf.get("aliases", {}).items():
        key = key_data.get(src["key"])
        if key is None:
            error(f"MISSING alias key {src['key']}")
        # re-use base data but replace apply_b64 and format_string
        credential, username, password, _, _ = key
        apply_b64 = src.get("b64", False)
        format_string = src.get("format")
        expose(env, alias, credential, username, password, apply_b64, format_string)
        vlog(
            f"aliasing {src['key']}"
            f" as environment variable {alias}"
            f" (b64: {apply_b64}, format: {format_string})"
        )
    return env
