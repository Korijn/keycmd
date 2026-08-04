import tomllib
from pathlib import Path
from pprint import pformat
from typing import Any, Literal, NotRequired, TypedDict, cast, overload

from .logs import vlog


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


@overload
def find_file(fname: str, first_only: Literal[True] = True) -> Path | None: ...


@overload
def find_file(fname: str, first_only: Literal[False]) -> list[Path]: ...


def find_file(fname: str, first_only: bool = True) -> Path | list[Path] | None:
    """Find a file by walking up the filesystem, starting at cwd"""
    cur = Path.cwd()
    home = Path.home()
    results: list[Path] = []
    while True:
        candidate = cur / fname
        if candidate.is_file():
            hit = candidate.resolve()
            if first_only:
                return hit
            else:
                results.append(hit)
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
    if not first_only:
        # return .keycmd files in order in which they should
        # be loaded and merged
        results.reverse()
        return results
    return None


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

    # .keycmd
    local_keycmds = find_file(".keycmd", first_only=False)
    for local_keycmd in local_keycmds:
        if local_keycmd == user_keyconf:
            vlog(f"skipping config file {local_keycmd} (already loaded)")
            continue
        vlog(f"loading config file {local_keycmd}")
        conf = merge_conf(conf, load_toml(local_keycmd))

    # pyproject.toml
    pyproj = find_file("pyproject.toml")
    if pyproj is not None:
        vlog(f"loading config file {pyproj}")
        conf = merge_conf(conf, load_pyproj(pyproj))

    vlog(f"merged config:\n{pformat(conf)}")

    # the config is user authored, so this is a statement of the shape keycmd
    # expects rather than a guarantee; get_env reports violations as user errors
    return cast(Conf, conf)
