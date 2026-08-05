# Installation

keycmd is a command line tool, so it wants to be installed **globally**, once per machine — not into the virtual environment of each project you use it on. It requires Python 3.13 or newer.

!!! note "Using WSL or pyenv?"

    Both need a slightly different approach. Skip ahead to [pyenv installation](#pyenv-installation), or to the [WSL guide](../guide/wsl.md), which explains why WSL users install keycmd on the Windows side.

## Global installation

The recommended way to install a Python command line tool is with [uv](https://docs.astral.sh/uv/):

=== "uv"

    ```bash
    uv tool install keycmd
    ```

=== "pipx"

    ```bash
    pipx install keycmd
    ```

=== "pip"

    ```bash
    pip install keycmd
    ```

`uv tool install` and `pipx` both put keycmd in an isolated environment of its own and put the executable on your `PATH`, which is exactly what you want for a tool that is not a dependency of anything.

Whichever you use, the `keycmd` executable has to end up in a folder that is on your `PATH`, or the command won't be available globally. If you were able to run `uv` or `pip` just now, the executable should land in the same place they did, and everything should be fine.

To verify keycmd is installed and available:

```bash
keycmd --version
```

Continue with the [Quick Start](quick-start.md).

## pyenv installation

If you're using pyenv, you're going to have to jump through a few hoops, since keycmd needs to be installed globally, which flies directly into the face of what pyenv is trying to accomplish.

This guide assumes you've also installed [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv), in order to get you the cleanest of setups. ✨

!!! note

    These instructions are for pyenv on Linux and macOS. If you are using pyenv-win on Windows, they are most likely not 100% compatible with your setup.

Run the following commands one by one to install keycmd into its own standalone environment:

```bash
pyenv virtualenv 3.13 keycmd
pyenv activate keycmd
pip install keycmd
pathToKeycmd=$(python -c 'import sys; from pathlib import Path; print(Path(sys.executable).parent / "keycmd")')
pyenv deactivate
mkdir -p $HOME/.local/bin
ln -s $pathToKeycmd $HOME/.local/bin/keycmd
```

Finally, edit your `~/.bashrc` file (or whatever shell profile you use) to include `~/.local/bin` in your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

!!! note

    This line may already be in place in your `~/.bashrc` — for example, if you installed poetry. It's a common trick used to expose specific binaries on `PATH` when they live in folders that also contain binaries that should *not* be exposed.

To verify keycmd is installed and available, run `keycmd --version`.

## Up- and downgrading

Install a different version the same way you installed the first one:

=== "uv"

    ```bash
    # upgrade to the latest release
    uv tool upgrade keycmd

    # install a specific version
    uv tool install keycmd==0.6.0
    ```

=== "pipx"

    ```bash
    pipx upgrade keycmd
    pipx install --force keycmd==0.6.0
    ```

=== "pip"

    ```bash
    pip install -U keycmd
    pip install keycmd==0.6.0
    ```

!!! note "pyenv"

    Activate the virtual environment first with `pyenv activate keycmd`, run `pip install -U keycmd`, and don't forget to `pyenv deactivate` afterwards. The symlink in `~/.local/bin` keeps working.
