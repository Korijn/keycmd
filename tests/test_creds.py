from os import environ

import pytest

from keycmd.creds import b64, expose, get_env


def test_b64():
    assert b64("fooß") == "Zm9vw58="


def test_expose():
    env = {}
    expose(env, "PLAIN", "cred", "user", "pw", False, None)
    expose(env, "ENCODED", "cred", "user", "pw", True, None)
    expose(env, "FORMATTED", "cred", "user", "pw", False, "{username}:{password}")
    expose(env, "BOTH", "cred", "user", "pw", True, "{credential}/{password}")
    assert env == {
        "PLAIN": "pw",
        "ENCODED": b64("pw"),
        "FORMATTED": "user:pw",
        "BOTH": b64("cred/pw"),
    }


def make_conf(credentials):
    return {
        "keys": {
            "__FOOBAR": {
                "credential": credentials.key,
                "username": credentials.username,
            },
            "__FOOBAR_B64": {
                "credential": credentials.key,
                "username": credentials.username,
                "b64": True,
            },
            "__FOOBAR_BASICAUTH": {
                "credential": credentials.key,
                "username": credentials.username,
                "format": "{username}:{password}",
                "b64": True,
            },
        },
        "aliases": {
            "__FOOBAR_B64_ALIAS": {
                "key": "__FOOBAR",
                "b64": True,
            },
            "__FOOBAR_BASICAUTH_ALIAS": {
                "key": "__FOOBAR",
                "format": "{username}:{password}",
                "b64": True,
            },
            "__FOOBAR_BASICAUTH_ALIAS2": {
                "key": "__FOOBAR_B64",
                "format": "{username}:{password}",
                "b64": True,
            },
        },
    }


def test_get_env(credentials):
    username = credentials.username
    password = credentials.password
    conf = make_conf(credentials)
    env = get_env(conf)
    all_keys = list(conf["keys"].keys())
    all_keys.extend(list(conf.get("aliases", {}).keys()))
    for k in all_keys:
        assert k not in environ
    assert env.get("__FOOBAR") == password
    assert env.get("__FOOBAR_B64") == b64(password)
    assert env.get("__FOOBAR_BASICAUTH") == b64(f"{username}:{password}")
    assert env.get("__FOOBAR_B64_ALIAS") == b64(password)
    assert env.get("__FOOBAR_BASICAUTH_ALIAS") == b64(f"{username}:{password}")
    assert env.get("__FOOBAR_BASICAUTH_ALIAS2") == b64(f"{username}:{password}")
    assert set(environ.keys()).intersection(set(env.keys())) == set(environ.keys())
    assert set(environ.keys()).symmetric_difference(set(env.keys())) == set(all_keys)


def test_get_env_no_keys(os_keyring):
    """An empty configuration passes the environment through untouched"""
    env = get_env({"keys": {}})
    assert env == dict(environ)


def test_get_env_verbose(capsys, credentials, verbose):
    get_env(make_conf(credentials))
    out = capsys.readouterr().out
    assert (
        f"exposing credential {credentials.key}"
        f" with user {credentials.username}"
        f" as environment variable __FOOBAR" in out
    )
    assert "aliasing __FOOBAR as environment variable __FOOBAR_B64_ALIAS" in out


def test_get_env_missing_credential(capsys, os_keyring):
    conf = {
        "keys": {
            "__FOOBAR": {
                "credential": "__keycmd_test_does_not_exist",
                "username": "nobody",
            },
        },
    }
    with pytest.raises(SystemExit) as exc_info:
        get_env(conf)
    assert exc_info.value.args[0] == 1
    assert "MISSING credential __keycmd_test_does_not_exist" in capsys.readouterr().err


def test_get_env_missing_alias_key(capsys, credentials):
    conf = {
        "keys": {
            "__FOOBAR": {
                "credential": credentials.key,
                "username": credentials.username,
            },
        },
        "aliases": {
            "__FOOBAR_ALIAS": {
                "key": "__DOES_NOT_EXIST",
            },
        },
    }
    with pytest.raises(SystemExit) as exc_info:
        get_env(conf)
    assert exc_info.value.args[0] == 1
    assert "MISSING alias key __DOES_NOT_EXIST" in capsys.readouterr().err
