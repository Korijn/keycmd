from pathlib import Path
from pprint import pformat

import tomli

from .logs import vlog


def load_toml(path):
    """Load a toml file"""
    with path.open("rb") as fh:
        try:
            return tomli.load(fh)
        except tomli.TOMLDecodeError as err:
            raise tomli.TOMLDecodeError(f"invalid TOML in {path}:\n{err}")


def load_pyproj(path):
    """Load [tool.keycmd] from a pyproject.toml file"""
    data = load_toml(path)
    return data.get("tool", {}).get("keycmd", {})


def defaults():
    """Generate the default config"""
    return {}


def merge_conf(a, b):
    """
    Merges two deep dictionary structures.
    All other datatypes are simply overwritten
    """
    a = a.copy()
    for key, value in b.items():
        if isinstance(value, dict):
            old_value = a.setdefault(key, {})
            a[key] = merge_conf(old_value, value)
        else:
            a[key] = value
    return a


def load_conf():
    """
    Load merged configuration from the following files:
    - defaults()
    - ~/.keycmd
    - ./.keycmd
    - first pyproject.toml found while walking file system up from .
    """
    conf = defaults()
    cwd = Path.cwd()

    # fixed conf locations, in order
    for path in [Path.home(), cwd]:
        fpath = path / ".keycmd"
        if fpath.is_file():
            vlog(f"loading config file {fpath}")
            conf = merge_conf(conf, load_toml(fpath))

    # dynamic conf locations, walk up from current directory
    cur = cwd
    while cur != cur.anchor:
        pyproj = cur / "pyproject.toml"
        if pyproj.is_file():
            vlog(f"loading config file {pyproj}")
            conf = merge_conf(conf, load_pyproj(pyproj))
            break
        # stop at the boundary of git repositories
        if (cur / ".git").is_dir():
            break
        cur = cur.parent

    vlog(f"merged config:\n{pformat(conf)}")

    return conf
