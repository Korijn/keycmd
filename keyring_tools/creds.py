import base64
from os import environ

import keyring


def b64(value):
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def get_env(conf):
    env = environ.copy()
    for key, src in conf["keys"].items():
        password = keyring.get_password(src["credential"], src["username"])
        if src.get("b64"):
            password = b64(password)
        env[key] = password
    return env
