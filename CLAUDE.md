# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`keycmd` runs a command with secrets from the OS keyring exposed as environment variables, so that credentials never have to live in a `.env` file. It supports Windows, macOS and Linux.

## Commands

```bash
uv sync                         # create the virtual environment
uv run pre-commit install       # the hooks run everything below on commit

uv run ruff check --fix
uv run ruff format
uv run ty check --error-on-warning
uv run pytest tests

uv run pytest tests/test_conf.py::test_load_conf     # a single test
uv run pytest -k "run_cmd and bash"                  # a single shell's parameters
```

## Testing

The tests that read and write credentials need an OS keyring that unlocks without user interaction. They skip themselves with a message when there is none, so the rest of the suite still runs; `KEYCMD_REQUIRE_OS_KEYRING=1` turns those skips into failures, and CI sets it. Windows needs no setup, macOS needs an unlocked keychain, and Linux needs the tests to run inside a d-bus session with `gnome-keyring` unlocked (see the Testing section of the README for the exact commands). `PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring` with `uv run --with keyrings.alt` avoids the OS keyring entirely.

`tests/test_wsl.py` covers calling the Windows install of keycmd from a shell inside WSL, and is opt in through `KEYCMD_TEST_WSL=1` on a Windows machine with WSL installed. `tests/test_wsl_interop.py` covers the same boundary as far as it can be reached without one, by faking the Windows process table, and runs everywhere. The rest of the suite stays off that code path entirely: the autouse `outside_wsl` fixture in `tests/conftest.py` clears the flags `wsl.py` detects with, so a run on Windows looks like a run anywhere else.

Things that bite in this suite:

- **Never assume a shell.** The `shell` fixture in `tests/conftest.py` parametrizes over every shell of the platform that is installed, so a test using it runs three times. Ask the `Shell` object for the dialect (`env_var`, `unset_env_var`, `command_not_found_statuses`) instead of branching on the platform. Shells that are not installed locally are covered by asserting on the command line keycmd builds for them.
- **`wsl.exe` mangles its command line**: backslashes disappear and quotes are stripped before the distribution sees them. Pass paths translated to `/mnt/...` by `wsl_path`, unquoted and free of spaces, and keep remote scripts on one line.
- Warnings are errors (`filterwarnings` in `pyproject.toml`), so a deprecation in a new Python release fails the suite rather than scrolling past.

## Architecture

`cli.main` wires the three halves together: `load_conf` produces the configuration, `get_env` turns it into an environment, and `run_cmd`/`run_shell` hand that environment to a shell. Errors reach the user through `logs.error`, which exits with status 1; `logs.vlog` output only appears under `--verbose` and is the first thing to reach for when debugging a configuration.

**`conf.py` — where the configuration comes from.** Later sources win, merged deeply by `merge_conf`: defaults, then `~/.keycmd`, then every `.keycmd` found walking up from the working directory (outermost first), then the first `pyproject.toml` found walking up, whose `[tool.keycmd]` table is used. `find_file` stops at a `.git` directory, at the home folder, and at the root of the file system, so the walk never escapes a repository. `USERPROFILE` is a module attribute so tests can point the user config elsewhere. The merged result is `cast` to `Conf` rather than validated: it is user authored, and `get_env` reports violations as user errors.

**`creds.py` — configuration to environment.** `get_env` copies `os.environ` and adds a variable per entry of `[keys]`, looking each credential up in the keyring; `[aliases]` re-expose an existing key under another name with different `b64`/`format` options, without a second keyring lookup. `expose` applies `format` first and `b64` second, which is what makes `{username}:{password}` basic auth work.

**`wsl.py` — the boundary between WSL and Windows.** WSL users install keycmd on Windows, which leaves it a Windows process with a Windows idea of a shell. `from_wsl` decides whether it was called from a distro — a `wsl.exe`/`wslhost.exe` ancestor decides it, a Windows shell found first decides against it, and a UNC working directory settles the rest — after which `run_shell`/`run_cmd` hand the work to `wsl.exe` rather than to a Windows shell. `KEYCMD_WSL` overrides that decision in either direction. Neither side of the boundary inherits the other's environment, so `share_env` lists the exposed variables in `WSLENV`, which is the only thing that crosses.

**`shell.py` — where the platform differences live.** `get_shell` asks shellingham which shell invoked the process and falls back to `$SHELL` or `%COMSPEC%`. `cmd` takes `/C` and keeps the command's arguments separate; every other shell takes `-c` and a single joined string. `exec` replaces the process with `execvpe` on posix, but runs a subprocess on Windows, which has no equivalent; `USE_SUBPROCESS` and the `IS_WINDOWS`/`IS_POSIX` flags are module attributes so tests can drive both paths on either platform.

## Conventions

The package is fully annotated and ships a `py.typed` marker, so `ANN` rules apply to `keycmd/` while the test suite is exempt. `ty` is configured with `python-version = "3.13"`, the oldest supported release, so it catches typing features that are newer than `requires-python` allows. CI matches that split: the latest Python on all three platforms, plus a single job on the oldest.
