import base64
from os import environ

import keyring

from .conf import Conf
from .logs import error, vlog
from .wsl import share_env

# credential, username, password, apply_b64, format string
KeyData = tuple[str, str, str, bool, str | None]


def b64(value: str) -> str:
    """Convert a string to its base64 representation"""
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def expose(
    env: dict[str, str],
    key: str,
    credential: str,
    username: str,
    password: str,
    apply_b64: bool,
    format_string: str | None,
) -> None:
    if format_string:
        password = format_string.format(
            credential=credential,
            username=username,
            password=password,
        )
    if apply_b64:
        password = b64(password)
    env[key] = password


def get_env(conf: Conf) -> dict[str, str]:
    """Load credentials from the OS keyring according to user configuration"""
    env = environ.copy()

    key_data: dict[str, KeyData] = {}
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

    for alias, alias_src in conf.get("aliases", {}).items():
        data = key_data.get(alias_src["key"])
        if data is None:
            error(f"MISSING alias key {alias_src['key']}")
        # re-use base data but replace apply_b64 and format_string
        credential, username, password, _, _ = data
        apply_b64 = alias_src.get("b64", False)
        format_string = alias_src.get("format")
        expose(env, alias, credential, username, password, apply_b64, format_string)
        vlog(
            f"aliasing {alias_src['key']}"
            f" as environment variable {alias}"
            f" (b64: {apply_b64}, format: {format_string})"
        )

    # an environment does not cross the boundary between WSL and windows
    # by itself, whichever side of it the command ends up running on
    share_env(env, [*conf["keys"], *conf.get("aliases", {})])
    return env
