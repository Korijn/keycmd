import os
from pathlib import Path

import tomli
import pytest

from keycmd.conf import load_toml, load_pyproj, defaults, merge_conf, load_conf


def test_defaults():
    # verify that defaults creates
    # a new dictionary every time
    assert defaults() is not defaults()


def test_load_toml(fs):
    path = Path("foo.toml")
    fs.create_file(path, contents="[keys]")
    doc = load_toml(path)
    assert doc["keys"] == {}

    path = Path("bar.toml")
    with pytest.raises(FileNotFoundError) as err:
        load_toml(path)

    path = Path("baz.toml")
    fs.create_file(path, contents="[keys}")
    with pytest.raises(tomli.TOMLDecodeError) as err:
        load_toml(path)
    assert path.name in err.value.args[0]


def test_load_pyproj(fs):
    path = Path("pyproject.toml")
    fs.create_file(path, contents="[tool.keycmd.keys]")
    doc = load_pyproj(path)
    assert doc["keys"] == {}

    path = Path("bar.toml")
    with pytest.raises(FileNotFoundError) as err:
        load_pyproj(path)

    path = Path("pyproject.toml")
    path.write_text("[keys}")
    with pytest.raises(tomli.TOMLDecodeError) as err:
        load_pyproj(path)
    assert path.name in err.value.args[0]


def test_merge_conf():
    a = {
        "keys": {
            "foo": {
                "bla": "bla",
            },
            "bar": {
                "bla": "bla",
            },
        }
    }
    b = {
        "something": "else",
        "keys": {
            "foo": {
                "bla": "blabla",
            },
            "baz": {
                "bla": "bla",
            },
        },
    }

    c = merge_conf(a, b)
    assert c == {
        "something": "else",
        "keys": {
            "foo": {"bla": "blabla"},
            "bar": {"bla": "bla"},
            "baz": {"bla": "bla"},
        },
    }

    d = {}
    e = merge_conf(a, d)
    assert e == {
        "keys": {
            "foo": {"bla": "bla"},
            "bar": {"bla": "bla"},
        },
    }


def create_pyproj_conf(relpath="."):
    pyproj_dir = Path(relpath)
    pyproj_dir.mkdir(exist_ok=True, parents=True)
    pyproj_path = (pyproj_dir / "pyproject.toml").resolve()
    pyproj_path.write_text(
        """[tool.keycmd.keys]
a = { foo = "bar" }
b = { foo = "bar" }
"""
    )
    return pyproj_path


def create_user_conf(user=".user/"):
    user_dir = Path(user).expanduser()
    user_dir.mkdir(exist_ok=True, parents=True)
    user_path = (user_dir / ".keycmd").resolve()
    user_path.write_text(
        """[keys]
a = { foo = "baz" }
c = { foo = "bar" }
"""
    )
    return user_path


def create_local_conf():
    local_path = Path(".keycmd")
    local_path.write_text(
        """[keys]
a = { foo = "quux" }
d = { foo = "bar" }
"""
    )
    return local_path


@pytest.fixture
def ch_tmpdir_deep(tmpdir):
    cwd = Path.cwd()
    tmpdir = Path(tmpdir) / "much" / "nested" / "so" / "deep"
    tmpdir.mkdir(parents=True)
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(cwd)


def test_load_conf(ch_tmpdir_deep):
    user_dir = ch_tmpdir_deep / ".user"

    pyproj_path = create_pyproj_conf()
    conf = load_conf(user=user_dir)
    assert conf == {
        "keys": {
            "a": {
                "foo": "bar",
            },
            "b": {
                "foo": "bar",
            },
        },
    }

    create_user_conf(user=user_dir)
    conf = load_conf(user=user_dir)
    assert conf == {
        "keys": {
            "a": {
                # pyproject.toml takes precedence
                "foo": "bar",
            },
            "b": {
                "foo": "bar",
            },
            "c": {
                "foo": "bar",
            },
        },
    }

    pyproj_path.unlink()
    conf = load_conf(user=user_dir)
    assert conf == {
        "keys": {
            "a": {
                "foo": "baz",
            },
            "c": {
                "foo": "bar",
            },
        },
    }

    create_local_conf()
    conf = load_conf(user=user_dir)
    assert conf == {
        "keys": {
            "a": {
                # .keycmd takes precedence
                "foo": "quux",
            },
            "c": {
                "foo": "bar",
            },
            "d": {
                "foo": "bar",
            },
        },
    }

    pyproj_path = create_pyproj_conf(relpath="..")
    conf = load_conf(user=user_dir)
    assert conf == {
        "keys": {
            "a": {
                # .keycmd takes precedence
                "foo": "quux",
            },
            "b": {
                "foo": "bar",
            },
            "c": {
                "foo": "bar",
            },
            "d": {
                "foo": "bar",
            },
        },
    }
