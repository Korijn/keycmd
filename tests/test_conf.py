import os
from pathlib import Path

import tomli
import pytest

import keycmd.conf
from keycmd.conf import load_toml, load_pyproj, defaults, merge_conf, load_conf


def test_defaults():
    # verify that defaults creates
    # a new dictionary every time
    assert defaults() is not defaults()


def test_load_toml(ch_tmpdir):
    path = Path("foo.toml")
    path.write_text("[keys]", encoding="utf-8")
    doc = load_toml(path)
    assert doc["keys"] == {}

    path = Path("bar.toml")
    with pytest.raises(FileNotFoundError) as err:
        load_toml(path)

    path = Path("baz.toml")
    path.write_text("[keys}", encoding="utf-8")
    with pytest.raises(tomli.TOMLDecodeError) as err:
        load_toml(path)
    assert path.name in err.value.args[0]


def test_load_pyproj(ch_tmpdir):
    path = Path("pyproject.toml")
    path.write_text("[tool.keycmd.keys]", encoding="utf-8")
    doc = load_pyproj(path)
    assert doc["keys"] == {}

    path = Path("bar.toml")
    with pytest.raises(FileNotFoundError) as err:
        load_pyproj(path)

    path = Path("pyproject.toml")
    path.write_text("[keys}", encoding="utf-8")
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
""",
        encoding="utf-8",
    )
    return pyproj_path


def create_user_conf():
    user_path = (keycmd.conf.USERPROFILE / ".keycmd").resolve()
    user_path.write_text(
        """[keys]
a = { foo = "baz" }
c = { foo = "bar" }
""",
        encoding="utf-8",
    )
    return user_path


def create_local_conf():
    local_path = Path(".keycmd")
    local_path.write_text(
        """[keys]
a = { foo = "quux" }
d = { foo = "bar" }
""",
        encoding="utf-8",
    )
    return local_path


@pytest.fixture
def userprofile(tmpdir, monkeypatch):
    user_dir = Path(tmpdir) / ".user"
    user_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(keycmd.conf, "USERPROFILE", user_dir)
    yield user_dir


@pytest.fixture
def ch_tmpdir(tmpdir):
    cwd = Path.cwd()
    tmpdir = Path(tmpdir) / "much" / "nested" / "so" / "deep"
    tmpdir.mkdir(parents=True)
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(cwd)


def test_load_conf(ch_tmpdir, userprofile):
    conf = load_conf()
    assert conf == {
        "keys": {},
    }

    pyproj_path = create_pyproj_conf()
    conf = load_conf()
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

    create_user_conf()
    conf = load_conf()
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
    conf = load_conf()
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
    conf = load_conf()
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
    conf = load_conf()
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
