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

uv sync --group docs && uv run mkdocs serve          # the docs site, with live reload
uv run mkdocs build --strict                         # what CI builds, warnings fatal
```

## Testing

The tests that read and write credentials need an OS keyring that unlocks without user interaction. They skip themselves with a message when there is none, so the rest of the suite still runs; `KEYCMD_REQUIRE_OS_KEYRING=1` turns those skips into failures, and CI sets it. Windows needs no setup, macOS needs an unlocked keychain, and Linux needs the tests to run inside a d-bus session with `gnome-keyring` unlocked (see `docs/development/testing.md` for the exact commands). `PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring` with `uv run --with keyrings.alt` avoids the OS keyring entirely.

`tests/test_wsl.py` covers calling the Windows install of keycmd from a shell inside WSL, and is opt in through `KEYCMD_TEST_WSL=1` on a Windows machine with WSL installed. `tests/test_wsl_interop.py` covers the same boundary as far as it can be reached without one, by faking the Windows process table, and runs everywhere. The rest of the suite stays off that code path entirely: the autouse `outside_wsl` fixture in `tests/conftest.py` clears the flags `wsl.py` detects with, so a run on Windows looks like a run anywhere else.

Things that bite in this suite:

- **Never assume a shell.** The `shell` fixture in `tests/conftest.py` parametrizes over every shell of the platform that is installed, so a test using it runs three times. Ask the `Shell` object for the dialect (`env_var`, `unset_env_var`, `command_not_found_statuses`) instead of branching on the platform. Shells that are not installed locally are covered by asserting on the command line keycmd builds for them.
- **`wsl.exe` mangles its command line**: backslashes disappear and quotes are stripped before the distribution sees them. Pass paths translated to `/mnt/...` by `wsl_path`, unquoted and free of spaces, and keep remote scripts on one line.
- **The remembered backend is redirected, always.** The autouse `cache_home` fixture in `tests/conftest.py` points `backend.CACHE_HOME` at a folder under `tmp_path`, so that a test run neither reads nor writes the note the machine it runs on is using, and every test starts with nothing remembered.
- **Do not assume the suite runs unpinned.** `PYTHON_KEYRING_BACKEND` is how the README suggests running the suite without an OS keyring, and it outranks everything `backend.py` does, so a test about remembering has to `delenv` it first or it will be testing the path that deliberately remembers nothing.
- Warnings are errors (`filterwarnings` in `pyproject.toml`), so a deprecation in a new Python release fails the suite rather than scrolling past.

## Documentation

The prose lives in the mkdocs site under `docs/`, built with mkdocs-material and deployed to GitHub Pages by `.github/workflows/docs.yml` on every push to `master` (pull requests build it without deploying, so a broken link fails before it lands). The nav in `mkdocs.yml` is explicit, so a new page has to be added there or the strict build fails on it. Screenshots live in `docs/assets/`.

The README is a landing page and nothing more: what it says about behaviour it says in a sentence, and links to the page that covers it. New prose belongs on the site — a section that grows in the README is a section that has drifted from its page.

## Architecture

`cli.main` wires the three halves together: `load_conf` produces the configuration, `get_env` turns it into an environment, and `run_cmd`/`run_shell` hand that environment to a shell. `--detect-backend` and `--reset-backend` return before any of it, since neither has a use for a configuration or a command. The command is an argparse `REMAINDER`, so everything from its first word onwards reaches it verbatim — including options keycmd has of its own — which leaves `end_of_options` to strip the `--` that argparse keeps in place, since only the first one is keycmd's to remove. Errors reach the user through `logs.error`, which exits with status 1 and takes the hint lines that go under the error with it; `logs.vlog` output only appears under `--verbose` and is the first thing to reach for when debugging a configuration.

**`conf.py` — where the configuration comes from.** Later sources win, merged deeply by `merge_conf`: defaults, then `~/.keycmd`, then every `.keycmd` found walking up from the working directory (outermost first), then the first `pyproject.toml` found walking up, whose `[tool.keycmd]` table is used. Both searches cover the same ground, so `load_conf` collects them in a single pass over `walk_up`, which stops at a `.git` directory, at the home folder, and at the root of the file system, so the walk never escapes a repository. `USERPROFILE` is a module attribute so tests can point the user config elsewhere. The merged result is `cast` to `Conf` rather than validated: it is user authored, and `get_env` reports violations as user errors.

**`creds.py` — configuration to environment.** `get_env` copies `os.environ` and adds a variable per entry of `[keys]`, looking each credential up in the backend `backend.load_backend` hands it; `[aliases]` re-expose an existing key under another name with different `b64`/`format` options, without a second keyring lookup. `expose` applies `format` first and `b64` second, which is what makes `{username}:{password}` basic auth work.

**`backend.py` — which keyring backend, and remembering the answer.** Left to itself keyring finds its backend by loading every backend every installed package registers, the single most expensive thing a run does. The answer only changes when the machine does, so `load_backend` writes it to `cache_path` — the platform's cache folder, `CACHE_HOME` being the module attribute tests redirect — and afterwards loads it with `load_keyring`, which is the same shortcut `PYTHON_KEYRING_BACKEND` buys without anyone having to know the variable exists. Everything about the note is treated as untrusted: `is_backend_name` keeps anything that is not a dotted class name from reaching an import, and a name that no longer loads (uninstalled, or a daemon that is no longer running, which `load_keyring` catches alike because it asks the class for its `priority`) sends the run back to searching. `backend_name` looks *through* the chainer, which is not a backend but the search wearing one's clothes, so writing it down would leave the search in place. `PYTHON_KEYRING_BACKEND` outranks the note and is never written over. Nothing is remembered when the search finds nothing: that and a `PYTHON_KEYRING_BACKEND` that cannot be loaded are reported as user errors with advice, rather than as the traceback that reaches the user otherwise. `detect_backend` and `reset_backend` are the deliberate versions of the two steps, for a machine that changed in a way that leaves the note valid but wrong.

**`wsl.py` — the boundary between WSL and Windows.** WSL users install keycmd on Windows, which leaves it a Windows process with a Windows idea of a shell. `from_wsl` decides whether it was called from a distro — a `wsl.exe`/`wslhost.exe` ancestor decides it, a Windows shell found first decides against it, and a UNC working directory settles the rest — after which `run_shell`/`run_cmd` hand the work to `wsl.exe` rather than to a Windows shell. A UNC working directory also names the distro, which `wsl_argv` passes as `--distribution` so that a second distro does not send the command to the default one. `KEYCMD_WSL` overrides that decision in either direction. Neither side of the boundary inherits the other's environment, so `share_env` lists the exposed variables in `WSLENV`, which is the only thing that crosses.

**`shell.py` — where the platform differences live.** `get_shell` asks shellingham which shell invoked the process and falls back to `$SHELL` or `%COMSPEC%`. `cmd` takes `/C` and keeps the command's arguments separate; every other shell takes `-c` and the single string `join_cmd` builds. Several arguments are an argv vector — the form the docs lead with, `keycmd npm install` — and `quote` protects each so that the shell does not split them into words a second time; one argument is already a command line, and is handed over as typed, so the shell interprets it. `quote` reaches for `shlex` for posix shells and doubles the quote for powershell, which also needs the call operator once its command name ends up quoted. `exec` replaces the process with `execvpe` on posix, but runs a subprocess on Windows, which has no equivalent; `USE_SUBPROCESS` and the `IS_WINDOWS`/`IS_POSIX` flags are module attributes so tests can drive both paths on either platform.

## Conventions

The package is fully annotated and ships a `py.typed` marker, so `ANN` rules apply to `keycmd/` while the test suite is exempt. `ty` is configured with `python-version = "3.13"`, the oldest supported release, so it catches typing features that are newer than `requires-python` allows. CI matches that split: the latest Python on all three platforms, plus a single job on the oldest.

keycmd sits in front of every command a user runs through it, so its own startup is latency the user pays each time. A handful of imports cost more than everything else in the package together, and none of them is needed on every run: `keyring` (and the backend it goes on to discover) only once a credential is looked up, `pprint` only under `--verbose`, and `subprocess` only on the Windows path, which cannot replace its own process. They are imported inside the function that needs them, which keeps `import keycmd.cli` at roughly a third of what it would otherwise cost, and `test_cli_import_stays_lean` fails if one of them wanders back up to module level. Reach for a lazy import when adding a dependency that most runs will not touch, and leave the rest at the top of the file where they belong.
