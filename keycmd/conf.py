from pathlib import Path
from pprint import pformat

import tomli

from .logs import vlog

# exposed for testing
USERPROFILE = "~"


def load_toml(path):
    """Load a toml file"""
    with path.open("rb") as fh:
        try:
            return tomli.load(fh)
        except tomli.TOMLDecodeError as err:
            raise tomli.TOMLDecodeError(f"invalid TOML in {path}:\n{err}") from err


def load_pyproj(path):
    """Load [tool.keycmd] from a pyproject.toml file"""
    data = load_toml(path)
    return data.get("tool", {}).get("keycmd", {})


def find_file(fname, first_only=True):
    """Find a file by walking up the filesystem, starting at cwd"""
    cur = Path.cwd()
    home = Path.home()
    results = []
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


def defaults():
    """Generate the default config"""
    return {"keys": {}}


def merge_conf(a, b):
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


def load_conf():
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

    return conf
