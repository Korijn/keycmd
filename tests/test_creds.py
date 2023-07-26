from os import environ

import keyring
import pytest

from keycmd.creds import b64, get_env


def test_b64():
    assert b64("fooß") == "Zm9vw58="


key = "__keycmd_testß"
username = "usernameß"
password = "passwordß"


@pytest.fixture
def credentials():
    keyring.set_password(key, username, password)
    yield
    keyring.delete_password(key, username)


def test_get_env(credentials):
    conf = {
        "keys": {
            "__FOOBAR": {
                "credential": key,
                "username": username,
            },
            "__FOOBAR_B64": {
                "credential": key,
                "username": username,
                "b64": True,
            },
        }
    }
    env = get_env(conf)
    assert "__FOOBAR" not in environ
    assert "__FOOBAR_B64" not in environ
    assert env.get("__FOOBAR") == password
    assert env.get("__FOOBAR_B64") == b64(password)
    assert set(environ.keys()).intersection(set(env.keys())) == set(environ.keys())
    assert set(environ.keys()).symmetric_difference(set(env.keys())) == set(
        conf["keys"].keys()
    )
