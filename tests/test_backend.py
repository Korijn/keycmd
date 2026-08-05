"""Finding a keyring backend once, and remembering which one it was

The search keyring runs to find a backend is the single most expensive
thing a keycmd run does, so keycmd writes the answer down and loads it by
name afterwards. What is asserted here is that the note is only ever
trusted as far as it can be checked: it has to look like a class name, it
has to still load, and it never stands in the way of PYTHON_KEYRING_BACKEND.
"""

from pathlib import Path
from typing import ClassVar

import keyring
import pytest
from keyring.backends.chainer import ChainerBackend
from keyring.backends.fail import Keyring as NoKeyring
from keyring.backends.null import Keyring as NullKeyring

import keycmd.backend
from keycmd.backend import (
    BACKEND_VAR,
    backend_name,
    cache_path,
    detect_backend,
    forget,
    is_backend_name,
    load_backend,
    recall,
    remember,
    reset_backend,
)

NULL = "keyring.backends.null.Keyring"


class FakeChainer(ChainerBackend):
    """A chainer with a fixed membership, instead of the one on this machine

    Subclassing a backend registers it with keyring, and a chainer of more
    than one backend outranks everything else, so the search any later
    test runs would settle on this one and find no credentials in it.
    Keyring skips a backend that says it is not viable, which is the way
    out of a registry there is no taking a class back out of.
    """

    viable: ClassVar = False
    backends: ClassVar = [NullKeyring(), NoKeyring()]


@pytest.fixture
def unpinned(monkeypatch):
    """A machine whose search finds a backend, and nothing remembered yet"""
    monkeypatch.delenv(BACKEND_VAR, raising=False)
    monkeypatch.setattr(keyring, "get_keyring", NullKeyring)
    return NullKeyring()


@pytest.fixture
def nothing_found(monkeypatch):
    """A machine whose search comes up empty"""
    monkeypatch.delenv(BACKEND_VAR, raising=False)
    monkeypatch.setattr(keyring, "get_keyring", NoKeyring)


def test_cache_path_per_platform(monkeypatch):
    """Each platform keeps discardable per user files somewhere of its own

    Covers the platforms the current one is not.
    """
    monkeypatch.setattr(keycmd.backend, "CACHE_HOME", None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/user")))

    monkeypatch.setattr(keycmd.backend, "IS_WINDOWS", True)
    monkeypatch.setattr(keycmd.backend, "IS_MACOS", False)
    monkeypatch.setenv("LOCALAPPDATA", "/local")
    assert cache_path() == Path("/local/keycmd/backend")
    monkeypatch.delenv("LOCALAPPDATA")
    assert cache_path() == Path("/home/user/AppData/Local/keycmd/backend")

    monkeypatch.setattr(keycmd.backend, "IS_WINDOWS", False)
    monkeypatch.setattr(keycmd.backend, "IS_MACOS", True)
    assert cache_path() == Path("/home/user/Library/Caches/keycmd/backend")

    monkeypatch.setattr(keycmd.backend, "IS_MACOS", False)
    monkeypatch.setenv("XDG_CACHE_HOME", "/xdg")
    assert cache_path() == Path("/xdg/keycmd/backend")
    monkeypatch.delenv("XDG_CACHE_HOME")
    assert cache_path() == Path("/home/user/.cache/keycmd/backend")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("keyring.backends.null.Keyring", True),
        ("a.B", True),
        # a bare name is not a class in a module, and importing it would
        # not give one either
        ("Keyring", False),
        ("", False),
        (".", False),
        ("keyring.backends..Keyring", False),
        # the file is fed to an import, so nothing that is not a name
        ("rm -rf /", False),
        ("keyring backends", False),
        ("a.b; import os", False),
    ],
)
def test_is_backend_name(name, expected):
    """Only the shape of a dotted class name is worth importing"""
    assert is_backend_name(name) is expected


def test_backend_name():
    """The name is one keyring can be given to load the backend again"""
    assert backend_name(NullKeyring()) == NULL
    assert isinstance(
        keyring.core.load_keyring(backend_name(NullKeyring())), NullKeyring
    )


def test_backend_name_chainer():
    """Writing down the chainer would leave the search it stands for in place

    So the backend it would have reached first is written down instead,
    which is where the credentials come from either way.
    """
    assert backend_name(FakeChainer()) == NULL


def test_remember_and_recall(cache_home):
    assert recall() is None
    remember(NULL)
    assert cache_path().read_text(encoding="utf-8") == f"{NULL}\n"
    assert recall() == NULL


def test_remember_replaces(cache_home):
    remember("keyring.backends.fail.Keyring")
    remember(NULL)
    assert recall() == NULL


def test_remember_leaves_no_temporary_file(cache_home):
    """The write goes through a temporary name, and does not stay there"""
    remember(NULL)
    assert [path.name for path in cache_path().parent.iterdir()] == ["backend"]


def test_remember_somewhere_unwritable(capsys, monkeypatch, tmp_path, verbose):
    """A cache that cannot be written is a slow run, not a failed one

    A file where the folder should be, which no amount of privilege makes
    writable, unlike a permission the suite may well be running above.
    """
    blocked = tmp_path / "blocked"
    blocked.write_text("not a folder", encoding="utf-8")
    monkeypatch.setattr(keycmd.backend, "CACHE_HOME", blocked / "cache")
    remember(NULL)
    assert "could not remember the keyring backend" in capsys.readouterr().out
    assert recall() is None


def test_recall_ignores_what_is_not_a_name(capsys, cache_home, verbose):
    """A file that has been scribbled in is worth no more than a search"""
    path = cache_path()
    path.parent.mkdir(parents=True)
    path.write_text("not a backend name\n", encoding="utf-8")
    assert recall() is None
    assert "does not name a keyring backend" in capsys.readouterr().out


def test_recall_ignores_an_unreadable_file(capsys, cache_home, verbose):
    """Which is what a directory in its place looks like from here"""
    cache_path().mkdir(parents=True)
    assert recall() is None
    assert "could not read" in capsys.readouterr().out


def test_forget(cache_home):
    assert forget() is False
    remember(NULL)
    assert forget() is True
    assert recall() is None


def test_load_backend_remembers(capsys, cache_home, unpinned, verbose):
    """The first run searches, and writes down what it found"""
    assert isinstance(load_backend(), NullKeyring)
    assert "(found in " in capsys.readouterr().out
    assert recall() == NULL


def test_load_backend_recalls(capsys, cache_home, unpinned, monkeypatch, verbose):
    """The runs after it load that backend by name instead of searching"""
    remember(NULL)

    def no_searching():
        raise AssertionError("searched for a backend with one already remembered")

    monkeypatch.setattr(keyring, "get_keyring", no_searching)
    assert isinstance(load_backend(), NullKeyring)
    assert "(remembered)" in capsys.readouterr().out


def test_load_backend_searches_again_when_the_note_is_stale(
    capsys, cache_home, unpinned, verbose
):
    """A backend that no longer loads sends the run back to searching

    load_keyring asks the class for its priority on the way, so this
    covers a backend that was uninstalled and one whose daemon stopped
    alike.
    """
    remember("nope.NotAKeyring")
    assert isinstance(load_backend(), NullKeyring)
    out = capsys.readouterr().out
    assert "no longer loads" in out
    # and the note is replaced rather than left to fail every run
    assert recall() == NULL


def test_load_backend_leaves_nothing_when_there_is_no_backend(
    cache_home, nothing_found
):
    """A search that found nothing is not an answer worth remembering"""
    with pytest.raises(SystemExit) as exc_info:
        load_backend()
    assert exc_info.value.args[0] == 1
    assert recall() is None


def test_load_backend_no_backend_message(capsys, cache_home, nothing_found):
    """A keyring with nothing behind it is a question, not a traceback"""
    with pytest.raises(SystemExit):
        load_backend()
    err = capsys.readouterr().err
    assert "no backend to read credentials from" in err
    assert BACKEND_VAR in err
    assert keycmd.backend.BACKENDS_URL in err


def test_load_backend_no_backend_in_wsl(capsys, monkeypatch, cache_home, nothing_found):
    """Inside a distribution there is a likelier answer than installing one"""
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu")
    with pytest.raises(SystemExit):
        load_backend()
    assert "inside WSL" in capsys.readouterr().err


def test_load_backend_pinned_wins(capsys, cache_home, monkeypatch, verbose):
    """PYTHON_KEYRING_BACKEND outranks anything keycmd wrote down"""
    remember("keyring.backends.fail.Keyring")
    monkeypatch.setenv(BACKEND_VAR, NULL)
    monkeypatch.setattr(keyring, "get_keyring", NullKeyring)
    assert isinstance(load_backend(), NullKeyring)
    assert f"keyring backend: {NullKeyring()} (named by {BACKEND_VAR})" in (
        capsys.readouterr().out
    )
    # and is left alone, since it was not keycmd that put it there
    assert recall() == "keyring.backends.fail.Keyring"


def test_load_backend_unloadable_pin(capsys, cache_home, monkeypatch):
    """A name keyring cannot load names the variable that carries it"""
    monkeypatch.setenv(BACKEND_VAR, "nope.NotAKeyring")

    def get_keyring():
        raise ModuleNotFoundError("No module named 'nope'")

    monkeypatch.setattr(keyring, "get_keyring", get_keyring)
    with pytest.raises(SystemExit) as exc_info:
        load_backend()
    assert exc_info.value.args[0] == 1
    err = capsys.readouterr().err
    assert f"{BACKEND_VAR}=nope.NotAKeyring could not be loaded" in err
    assert "ModuleNotFoundError" in err


def test_detect_backend(capsys, cache_home, unpinned):
    """Searching on purpose, for when the machine changed under the note"""
    remember("keyring.backends.fail.Keyring")
    detect_backend()
    assert f"remembered keyring backend {NULL}, found in " in capsys.readouterr().out
    assert recall() == NULL


def test_detect_backend_with_nothing_to_find(capsys, cache_home, nothing_found):
    with pytest.raises(SystemExit) as exc_info:
        detect_backend()
    assert exc_info.value.args[0] == 1
    assert "no backend to read credentials from" in capsys.readouterr().err
    assert recall() is None


def test_detect_backend_with_a_pin(capsys, cache_home, monkeypatch):
    """There is nothing to remember when keyring is already being told"""
    monkeypatch.setenv(BACKEND_VAR, NULL)
    detect_backend()
    assert f"{BACKEND_VAR}={NULL} already names the backend" in capsys.readouterr().out
    assert recall() is None


def test_reset_backend(capsys, cache_home):
    remember(NULL)
    reset_backend()
    assert "forgot the remembered keyring backend" in capsys.readouterr().out
    assert recall() is None


def test_reset_backend_with_nothing_remembered(capsys, cache_home):
    reset_backend()
    assert "no keyring backend was remembered" in capsys.readouterr().out
