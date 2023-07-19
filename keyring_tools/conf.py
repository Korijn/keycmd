from pathlib import Path

import tomli


def load_toml(path):
    """Load a toml file"""
    with path.open("rb") as fh:
        return tomli.load(fh)


def load_pyproj(path):
    """Load [tool.keyring-tools] from a pyproject.toml file"""
    data = load_toml(path)
    return data.get("tool", {}).get("keyring-tools", {})


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
    - ~/.keyring-tools
    - ./.keyring-tools
    - first pyproject.toml found while walking file system up from .
    """
    conf = defaults()
    cwd = Path.cwd()

    # fixed conf locations, in order
    for path in [Path.home(), cwd]:
        fpath = path / ".keyring-tools"
        if fpath.is_file():
            conf = merge_conf(conf, load_toml(fpath))

    # dynamic conf locations, walk up from current directory
    cur = cwd
    while cur != cur.anchor:
        pyproj = cur / "pyproject.toml"
        if pyproj.is_file():
            conf = merge_conf(conf, load_pyproj(pyproj))
            break
        # stop at the boundary of git repositories
        if (cur / ".git").is_dir():
            break
        cur = cur.parent

    return conf
