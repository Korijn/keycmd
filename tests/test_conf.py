import os
import tomllib
from pathlib import Path

import pytest

import keycmd.conf
from keycmd.conf import (
    defaults,
    find_file,
    load_conf,
    load_pyproj,
    load_toml,
    merge_conf,
)


@pytest.fixture
def ch_tmpdir(tmp_path):
    """Run deep inside an empty directory tree, outside of any git repository

    Overrides the shallow fixture from conftest, so that the tests below
    have room to walk up the file system.
    """
    cwd = Path.cwd()
    deep = tmp_path / "much" / "nested" / "so" / "deep"
    deep.mkdir(parents=True)
    os.chdir(deep)
    yield deep
    os.chdir(cwd)


def set_home(monkeypatch, home):
    """Pretend the home folder is somewhere else"""
    home = Path(home)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


def create_path(p):
    p = Path(p).expanduser().resolve()
    p.parent.mkdir(exist_ok=True, parents=True)
    p.touch()
    return p


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
    with pytest.raises(tomllib.TOMLDecodeError) as err:
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
    with pytest.raises(tomllib.TOMLDecodeError) as err:
        load_pyproj(path)
    assert path.name in err.value.args[0]


def test_find_file(ch_tmpdir, monkeypatch, tmp_path):
    # the walk stops just below the home folder
    home = set_home(monkeypatch, tmp_path)
    p1 = create_path("../.blabla")
    p2 = create_path("../../.blabla")
    p3 = create_path("../../../.blabla")
    create_path(home / ".blabla")
    assert find_file(".blabla") == p1
    assert find_file(".blabla", first_only=False) == [p3, p2, p1]
    (p2.parent / ".git").mkdir(exist_ok=True, parents=True)
    assert find_file(".blabla", first_only=False) == [p2, p1]


def test_find_file_missing(ch_tmpdir, monkeypatch, tmp_path):
    set_home(monkeypatch, tmp_path)
    assert find_file(".blabla") is None
    assert find_file(".blabla", first_only=False) == []


def test_find_file_stops_at_filesystem_root(ch_tmpdir, monkeypatch, tmp_path):
    # a home folder that is nowhere near the current directory, so the walk
    # runs all the way into the root of the file system instead of stopping
    # at the home folder
    set_home(monkeypatch, tmp_path / "somewhere" / "else")
    p = create_path(".blabla")
    assert find_file(".blabla", first_only=False) == [p]


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
    user_path = (Path(keycmd.conf.USERPROFILE) / ".keycmd").resolve()
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


def test_load_conf_home_is_cwd(capsys, ch_tmpdir, monkeypatch, verbose):
    """The user config is not merged twice when it is also a local config"""
    monkeypatch.setattr(keycmd.conf, "USERPROFILE", ch_tmpdir)
    user_path = create_user_conf()
    conf = load_conf()
    out = capsys.readouterr().out
    assert f"loading config file {user_path}" in out
    assert f"skipping config file {user_path} (already loaded)" in out
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


def test_load_conf_expands_user(ch_tmpdir, monkeypatch, tmp_path):
    """The user config path understands ~"""
    home = set_home(monkeypatch, tmp_path / "fake-home")
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr(keycmd.conf, "USERPROFILE", "~")
    (home / ".keycmd").write_text(
        """[keys]
a = { foo = "bar" }
""",
        encoding="utf-8",
    )
    assert load_conf() == {"keys": {"a": {"foo": "bar"}}}
