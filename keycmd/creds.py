import base64
from os import environ

from .backend import load_backend
from .conf import AliasConf, Conf, KeyConf
from .logs import error, vlog
from .wsl import share_env

# credential, username, password
KeyData = tuple[str, str, str]


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


def expose_conf(
    env: dict[str, str],
    name: str,
    data: KeyData,
    src: KeyConf | AliasConf,
    what: str,
) -> None:
    """Expose a credential under the b64 and format options of one config entry

    A key and an alias differ in where the credential comes from, not in
    what happens to it on the way into the environment.
    """
    apply_b64 = src.get("b64", False)
    format_string = src.get("format")
    expose(env, name, *data, apply_b64, format_string)
    vlog(
        f"{what} as environment variable {name}"
        f" (b64: {apply_b64}, format: {format_string})"
    )


def get_env(conf: Conf) -> dict[str, str]:
    """Load credentials from the OS keyring according to user configuration"""
    env = environ.copy()

    key_data: dict[str, KeyData] = {}
    keys = conf["keys"]
    if keys:
        # which backend the credentials come from is the first thing to
        # check when they are not the ones that were expected, and
        # load_backend reports it under --verbose
        backend = load_backend()

        for key, src in keys.items():
            credential = src["credential"]
            username = src["username"]
            password = backend.get_password(credential, username)
            if password is None:
                error(
                    f"MISSING credential {credential}"
                    f" with user {username}"
                    f" as it does not exist"
                )
            key_data[key] = (credential, username, password)
            expose_conf(
                env,
                key,
                key_data[key],
                src,
                f"exposing credential {credential} with user {username}",
            )

    aliases = conf.get("aliases", {})
    for alias, alias_src in aliases.items():
        # the credential is already in hand, only the options differ
        data = key_data.get(alias_src["key"])
        if data is None:
            error(f"MISSING alias key {alias_src['key']}")
        expose_conf(env, alias, data, alias_src, f"aliasing {alias_src['key']}")

    # an environment does not cross the boundary between WSL and windows
    # by itself, whichever side of it the command ends up running on
    share_env(env, [*keys, *aliases])
    return env
