import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

from .logs import vlog, vlog_pretty


class KeyConf(TypedDict):
    """A single entry of the [keys] table"""

    credential: str
    username: str
    b64: NotRequired[bool]
    format: NotRequired[str]


class AliasConf(TypedDict):
    """A single entry of the [aliases] table"""

    key: str
    b64: NotRequired[bool]
    format: NotRequired[str]


class Conf(TypedDict):
    """The merged keycmd configuration"""

    keys: dict[str, KeyConf]
    aliases: NotRequired[dict[str, AliasConf]]


# exposed for testing
USERPROFILE: str | Path = "~"


def load_toml(path: Path) -> dict[str, Any]:
    """Load a toml file"""
    with path.open("rb") as fh:
        try:
            return tomllib.load(fh)
        except tomllib.TOMLDecodeError as err:
            # name the offending file in the error, by rewriting the message
            # of the original rather than raising a new one: the single
            # argument constructor is deprecated as of python 3.14, and the
            # structured one that replaces it does not exist before it
            err.args = (f"invalid TOML in {path}:\n{err}",)
            raise


def load_pyproj(path: Path) -> dict[str, Any]:
    """Load [tool.keycmd] from a pyproject.toml file"""
    data = load_toml(path)
    return data.get("tool", {}).get("keycmd", {})


def walk_up() -> Iterator[Path]:
    """Yield the working directory and its parents, nearest first

    The walk stops at a git repository, so that it never leaves one, and
    otherwise just below the home folder or at the root of the file system.
    """
    cur = Path.cwd()
    home = Path.home()
    while True:
        yield cur
        # don't search outside git repositories
        if (cur / ".git").is_dir():
            break
        # stop before searching the home folder
        if cur.parent == home:
            break
        # stop if we can't go up anymore
        if cur.parent == cur:
            break
        cur = cur.parent


def defaults() -> dict[str, Any]:
    """Generate the default config"""
    return {"keys": {}}


def merge_conf(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """
    Merges two deep dictionary structures.
    All other datatypes are simply overwritten
    """
    a = a.copy()
    for key, value in b.items():
        if isinstance(value, dict):
            old_value = a.get(key, {})
            a[key] = merge_conf(old_value, value)
        else:
            a[key] = value
    return a


def load_conf() -> Conf:
    """
    Load merged configuration from the following files:
    - defaults()
    - ~/.keycmd
    - all .keycmd found while walking file system up from .
    - first pyproject.toml found while walking file system up from .
    """
    conf = defaults()

    # ~/.keycmd
    user_keyconf = (Path(USERPROFILE).expanduser() / ".keycmd").resolve()
    if user_keyconf.is_file():
        vlog(f"loading config file {user_keyconf}")
        conf = merge_conf(conf, load_toml(user_keyconf))

    # both searches cover the same ground, so they share a single walk
    local_keycmds: list[Path] = []
    pyproj: Path | None = None
    for directory in walk_up():
        candidate = directory / ".keycmd"
        if candidate.is_file():
            local_keycmds.append(candidate.resolve())
        if pyproj is None:
            candidate = directory / "pyproject.toml"
            if candidate.is_file():
                pyproj = candidate.resolve()

    # .keycmd, outermost first, so that the nearest one wins
    for local_keycmd in reversed(local_keycmds):
        if local_keycmd == user_keyconf:
            vlog(f"skipping config file {local_keycmd} (already loaded)")
            continue
        vlog(f"loading config file {local_keycmd}")
        conf = merge_conf(conf, load_toml(local_keycmd))

    # pyproject.toml
    if pyproj is not None:
        vlog(f"loading config file {pyproj}")
        conf = merge_conf(conf, load_pyproj(pyproj))

    vlog_pretty("merged config:\n", conf)

    # the config is user authored, so this is a statement of the shape keycmd
    # expects rather than a guarantee; get_env reports violations as user errors
    return cast(Conf, conf)
