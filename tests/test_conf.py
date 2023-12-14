import os
from pathlib import Path

import pytest
import tomli

import keycmd.conf
from keycmd.conf import (
    defaults,
    find_file,
    load_conf,
    load_pyproj,
    load_toml,
    merge_conf,
)


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


def create_path(p):
    p = Path(p).expanduser().resolve()
    p.parent.mkdir(exist_ok=True, parents=True)
    p.touch()
    return p


def test_find_file(ch_tmpdir):
    p1 = create_path("../.blabla")
    p2 = create_path("../../.blabla")
    p3 = create_path("../../../.blabla")
    create_path("~/.blabla")
    assert find_file(".blabla") == p1
    assert find_file(".blabla", first_only=False) == [p3, p2, p1]
    (p2.parent / ".git").mkdir(exist_ok=True, parents=True)
    assert find_file(".blabla", first_only=False) == [p2, p1]


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


def create_local_conf(
    relpath=".",
    content="""[keys]
a = { foo = "quux" }
d = { foo = "bar" }
""",
):
    local_dir = Path(relpath)
    local_dir.mkdir(exist_ok=True, parents=True)
    local_path = (local_dir / ".keycmd").resolve()
    local_path.write_text(
        content,
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
                "foo": "bar",
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

    create_local_conf(
        relpath="..",
        content="""[keys]
e = { foo = "quux" }
""",
    )
    conf = load_conf()
    assert conf == {
        "keys": {
            "a": {
                "foo": "bar",
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
            "e": {
                "foo": "quux",
            },
        },
    }
