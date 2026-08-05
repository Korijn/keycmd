# Testing

```bash
uv run pytest tests

uv run pytest tests/test_conf.py::test_load_conf   # a single test
uv run pytest -k "run_cmd and bash"                # a single shell's parameters
```

CI runs the test suite on Windows, macOS and Linux on the latest Python, plus one job on the oldest supported Python to catch anything newer than it allows.

The suite adapts to the platform it runs on. It exercises every shell of the platform that is installed — `sh`, `bash` and `zsh` on posix, `cmd` and `powershell` on Windows, and `pwsh` on either, since it installs everywhere and quotes its own way — and it skips the process replacement tests on Windows, which has no `execvpe`.

## A keyring to test against

The tests that read and write credentials need a real OS keyring that can be unlocked without user interaction. They are skipped with a message if there is no such keyring, so the rest of the suite still runs. Set `KEYCMD_REQUIRE_OS_KEYRING=1` to turn those skips into failures instead; CI sets it, so that a broken keyring setup can't quietly reduce the coverage of a run.

=== "Windows"

    The credential manager is available to your session out of the box, no setup needed.

=== "macOS"

    Your login keychain works as long as it is unlocked. CI instead creates a throwaway keychain and makes it the default:

    ```bash
    security create-keychain -p keycmd-test keycmd-test.keychain
    security set-keychain-settings keycmd-test.keychain
    security unlock-keychain -p keycmd-test keycmd-test.keychain
    security list-keychains -d user -s keycmd-test.keychain login.keychain
    security default-keychain -s keycmd-test.keychain
    ```

=== "Linux"

    The secret service is bound to a d-bus session, so the tests have to run inside one, with an unlocked keyring daemon. Install `gnome-keyring` and `dbus-x11` first:

    ```bash
    dbus-run-session -- bash -c '
      printf "%s" keycmd-test | gnome-keyring-daemon --unlock --components=secrets
      uv run pytest tests
    '
    ```

If you would rather not involve your OS keyring at all, point keyring at a file-based backend:

```bash
uv run --with keyrings.alt pytest tests
# with PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring set in your environment
```

## Testing WSL

The [WSL setup](../guide/wsl.md) has two halves.

Working *inside* WSL, keycmd is a posix process like any other, talking to whichever keyring backend the distribution provides; that is the Linux job above, keyring daemon and all.

The other half — calling the Windows install of keycmd from a WSL shell to reach the Windows credential manager — crosses the interop boundary, and that is what `tests/test_wsl.py` covers: a credential in the credential manager, a shell inside WSL, and the Windows install of keycmd in between.

Everything about that boundary that can be decided without a Windows machine is in `tests/test_wsl_interop.py` instead, and runs everywhere: which process tree and working directory mean keycmd was called from a distribution, the command lines it builds for `wsl.exe`, and the `WSLENV` that carries the credentials across.

The end to end tests are opt in, because installing WSL takes a CI job of its own. On a Windows machine that has WSL installed:

```powershell
$env:KEYCMD_TEST_WSL = 1
uv run pytest tests/test_wsl.py
```

## Things that bite in this suite

* **Never assume a shell.** The `shell` fixture parametrizes over every shell of the platform that is installed, so a test using it runs several times. Ask the `Shell` object for the dialect (`env_var`, `unset_env_var`, `command_not_found_statuses`) instead of branching on the platform.
* **`wsl.exe` mangles its command line**: backslashes disappear and quotes are stripped before the distribution sees them. Pass paths translated to `/mnt/...` by `wsl_path`, unquoted and free of spaces, and keep remote scripts on one line.
* **The remembered backend is redirected, always.** An autouse fixture points `backend.CACHE_HOME` at a folder under `tmp_path`, so a test run neither reads nor writes the note the machine it runs on is using.
* **Do not assume the suite runs unpinned.** `PYTHON_KEYRING_BACKEND` outranks everything `backend.py` does, so a test about remembering has to `delenv` it first, or it will be testing the path that deliberately remembers nothing.
* **Warnings are errors**, so a deprecation in a new Python release fails the suite rather than scrolling past.
