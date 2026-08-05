"""Which keyring backend to use, and remembering the answer

Left to itself, keyring works out which backend to use by loading every
backend that every installed package registers and keeping the best of
them. That search runs again on each invocation and is the single most
expensive thing a keycmd run does, on a machine with a few packages
installed more than the whole of the rest of a run put together.

The answer, though, is the same every time until the packages on the
machine change, so keycmd writes it down the first time and loads that
backend by name afterwards, which is the same shortcut
PYTHON_KEYRING_BACKEND is for without anyone having to know the variable
exists. What is written down is only ever an answer keycmd can check:
`load_keyring` refuses a backend that is not installed and one that is
not viable alike, so a note that has gone stale sends the run back to
searching rather than failing it. `--detect-backend` and
`--reset-backend` are the deliberate versions of the same two steps, for
when the machine changed in a way that the note is still a valid answer
to.
"""

import os
import sys
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, NoReturn

from .logs import error, log, vlog, vwarn
from .wsl import in_distro

if TYPE_CHECKING:
    # keyring is the most expensive import in the package and a run that
    # looks up no credential never makes it, so the annotations below are
    # the only place its name may appear at module level
    from keyring.backend import KeyringBackend

# keyring's own way to be told which backend to use, which skips the
# search by itself and outranks anything keycmd wrote down
BACKEND_VAR: str = "PYTHON_KEYRING_BACKEND"

# exposed for testing, so that a run on one platform can drive the paths
# of the others
IS_WINDOWS: bool = os.name == "nt"
IS_MACOS: bool = sys.platform == "darwin"
CACHE_HOME: Path | None = None

# where someone whose machine turned out to have no backend can find one
BACKENDS_URL: str = "https://github.com/jaraco/keyring#third-party-backends"


def cache_home() -> Path:
    """Where this platform keeps per user files a program can afford to lose

    Which is what this is: everything under it can be deleted at any
    moment, and the next run pays for a search and writes it again.
    """
    if CACHE_HOME is not None:
        return CACHE_HOME
    if IS_WINDOWS:
        # the local one rather than the roaming one, since which backends
        # a machine has is a fact about that machine
        local = os.environ.get("LOCALAPPDATA")
        return Path(local) if local else Path.home() / "AppData" / "Local"
    if IS_MACOS:
        return Path.home() / "Library" / "Caches"
    xdg = os.environ.get("XDG_CACHE_HOME")
    return Path(xdg) if xdg else Path.home() / ".cache"


def cache_path() -> Path:
    """The file the remembered backend is written to"""
    return cache_home() / "keycmd" / "backend"


def is_backend_name(name: str) -> bool:
    """Does this look like the dotted class name it is supposed to be?

    What comes out of the file is fed to an import, so what goes in has
    to be the shape of a name and nothing else. Anything keycmd wrote is;
    a file that has since been truncated or scribbled in is not, and is
    worth no more than a fresh search.
    """
    parts = name.split(".")
    return len(parts) > 1 and all(part.isidentifier() for part in parts)


def recall() -> str | None:
    """The backend an earlier run wrote down, if one did"""
    path = cache_path()
    try:
        name = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        vlog(f"no keyring backend remembered in {path}")
        return None
    except OSError as err:
        vwarn(f"could not read {path}: {err!r}")
        return None
    if not is_backend_name(name):
        vwarn(f"{path} does not name a keyring backend")
        return None
    return name


def remember(name: str) -> None:
    """Write the backend down, so that the next run can skip the search

    Through a temporary file, so that a second keycmd running at the same
    moment reads either the old name or the new one rather than half of
    each. Somewhere unwritable is a reason to search every run, not a
    reason to fail the one that already has its answer.
    """
    path = cache_path()
    temp = path.with_name(f"{path.name}.{os.getpid()}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(f"{name}\n", encoding="utf-8")
        os.replace(temp, path)
    except OSError as err:
        vwarn(f"could not remember the keyring backend in {path}: {err!r}")
        # clearing up after the failed write cannot be allowed to fail in
        # its turn, since whatever stopped the write stops this just as
        # easily, and missing_ok covers only the file that is not there
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        return
    vlog(f"remembered keyring backend {name} in {path}")


def forget() -> bool:
    """Drop what was written down, if anything was"""
    path = cache_path()
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    except OSError as err:
        error(f"could not forget the keyring backend in {path}: {err!r}")
    vlog(f"removed {path}")
    return True


def load_named(name: str) -> "KeyringBackend | None":
    """The named backend, if it can still be loaded

    load_keyring asks the class for its priority on the way, which is how
    keyring itself decides a backend is viable, so a backend that has
    been uninstalled and one whose daemon is no longer running both come
    back as nothing here.
    """
    from keyring.core import load_keyring

    try:
        return load_keyring(name)
    except Exception as err:
        vlog(f"remembered keyring backend {name} no longer loads: {err!r}")
        return None


def search() -> tuple["KeyringBackend", float]:
    """Let keyring find a backend, and time how long it took"""
    import keyring

    start = perf_counter()
    backend = keyring.get_keyring()
    return backend, perf_counter() - start


def backend_name(backend: "KeyringBackend") -> str:
    """The name that loads this backend again without searching

    The chainer is not a backend of its own but the search over all of
    them wearing one's clothes, so writing it down would leave the search
    in place. What is worth writing down is the backend the chainer would
    have reached first, which is where the credentials of an unremembered
    run come from anyway.
    """
    from keyring.backends.chainer import ChainerBackend

    if isinstance(backend, ChainerBackend):
        # sorted by priority, and the chainer only wins when it has more
        # than one to sort, but it costs nothing to not assume that
        chained = backend.backends
        if chained:
            backend = chained[0]
    cls = type(backend)
    return f"{cls.__module__}.{cls.__qualname__}"


def is_no_backend(backend: "KeyringBackend") -> bool:
    """Is this the backend keyring settles on when it found nothing?"""
    from keyring.backends.fail import Keyring

    return isinstance(backend, Keyring)


def no_backend() -> NoReturn:
    """Report a keyring that has nowhere to read credentials from

    It raises on the first lookup otherwise, which reaches the user as a
    traceback rather than as an answer to the question they have.
    """
    hints = [
        f"install one for this platform, or name one you have with {BACKEND_VAR}",
        f"see {BACKENDS_URL}",
    ]
    if in_distro():
        # the README tells WSL users to install keycmd on windows for
        # exactly this reason, and this is what not having done so looks
        # like from inside the distribution
        hints.append(
            "inside WSL this usually means no keyring daemon is running;"
            " the README explains how to reach the windows credential"
            " manager instead"
        )
    error("keyring has no backend to read credentials from", *hints)


def pinned_backend(pinned: str) -> "KeyringBackend":
    """The backend PYTHON_KEYRING_BACKEND names

    Which keyring loads without searching, so there is nothing here for
    keycmd to remember or to have remembered.
    """
    import keyring

    try:
        backend = keyring.get_keyring()
    except Exception as err:
        error(
            f"{BACKEND_VAR}={pinned} could not be loaded: {err!r}",
            f"name a backend class that is installed, or unset {BACKEND_VAR}"
            f" to let keycmd find one itself",
        )
    vlog(f"keyring backend: {backend} (named by {BACKEND_VAR})")
    return backend


def load_backend() -> "KeyringBackend":
    """The keyring backend to read this run's credentials from"""
    pinned = os.environ.get(BACKEND_VAR, "")
    if pinned:
        return pinned_backend(pinned)

    name = recall()
    if name is not None:
        backend = load_named(name)
        if backend is not None:
            vlog(f"keyring backend: {backend} (remembered)")
            return backend
        # whatever it named is gone, and the note is worth nothing now
        forget()

    backend, elapsed = search()
    vlog(f"keyring backend: {backend} (found in {elapsed:.2f}s)")
    if is_no_backend(backend):
        # nothing worth writing down, and nothing to read credentials from
        no_backend()
    remember(backend_name(backend))
    return backend


def detect_backend() -> None:
    """Search for a backend now, and write down what turns up

    The search runs by itself on the first run that needs a credential.
    This is for the runs after that, once the machine has changed in a
    way that makes the old answer the wrong one rather than an invalid
    one: a backend installed that outranks the one in use, or one
    uninstalled that keyring can still load.
    """
    pinned = os.environ.get(BACKEND_VAR, "")
    if pinned:
        log(f"{BACKEND_VAR}={pinned} already names the backend to use")
        return
    backend, elapsed = search()
    if is_no_backend(backend):
        no_backend()
    name = backend_name(backend)
    remember(name)
    log(f"remembered keyring backend {name}, found in {elapsed:.2f}s")


def reset_backend() -> None:
    """Forget the backend, so that the next run searches for one again"""
    if forget():
        log("forgot the remembered keyring backend")
    else:
        log("no keyring backend was remembered")
