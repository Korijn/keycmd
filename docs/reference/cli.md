# CLI Reference

```
❯ keycmd --help
usage: keycmd [-h] [-v] [--version] [--detect-backend] [--reset-backend]
              [--shell]
              ...

positional arguments:
  command           command to run

options:
  -h, --help        show this help message and exit
  -v, --verbose     enable verbose output, useful for configuration debugging
  --version         print version info
  --detect-backend  search for the keyring backend now and remember it for
                    later runs
  --reset-backend   forget the remembered keyring backend, so the next run
                    searches again
  --shell           spawn a subshell instead of running a command
```

## Positional arguments

### `command`

The command to run with the credentials exposed as environment variables.

Given as a single quoted argument, it is handed to your shell as typed, so the shell interprets it — pipes, redirects and variable expansion included:

```bash
keycmd 'echo $SECRET | tr a-z A-Z'
```

Given as several arguments, each is passed on as the word it was, and shell syntax is not interpreted a second time:

```bash
keycmd mytool --message 'hello world'
```

Required, unless `--shell`, `--version`, `--detect-backend` or `--reset-backend` is used. Without one, keycmd exits with `error: missing command argument`.

See [running commands](../guide/running-commands.md) for the full story.

## Options

### `-v`, `--verbose`

Report every step: the configuration files loaded, the merged configuration, where the keyring backend came from, each credential exposed, the shell detected, and the command line run. See [troubleshooting](../guide/troubleshooting.md).

Values of credentials are never printed.

### `--version`

Print the installed version and exit.

### `--shell`

Spawn an interactive subshell with the credentials exposed, instead of running a command. Everything started from that subshell inherits them, until you exit it.

### `--detect-backend`

Search for a keyring backend now, and remember it for later runs. Returns without loading a configuration or running a command.

Use it when your machine changed in a way that leaves the remembered answer valid but wrong — a better backend installed, or a package removed whose backend you no longer want. See [keyring backends](../guide/keyring-backends.md).

### `--reset-backend`

Forget the remembered keyring backend, so the next run searches again. Also returns without loading a configuration.

## Environment variables

### `PYTHON_KEYRING_BACKEND`

keyring's own setting, naming the backend class to use, e.g. `keyring.backends.SecretService.Keyring`. It skips the search entirely and outranks anything keycmd has remembered — and with it set, keycmd remembers nothing of its own. Run `keyring --list-backends` for the names to choose from.

### `KEYCMD_WSL`

Override keycmd's detection of whether it was called from a WSL distribution. Set it to `0` to keep the run on the Windows side, or to anything else to send it through `wsl.exe` regardless. See the [WSL guide](../guide/wsl.md).

### `WSLENV`

Not a setting of keycmd's, but the mechanism it uses: only variables listed in `WSLENV` cross the boundary between Windows and a WSL distribution, so keycmd appends the variables from your configuration to whatever you already had listed there.

## Files

| Path | What it is |
| --- | --- |
| `~/.keycmd` | your user-wide configuration |
| `./.keycmd` | per-directory configuration, all of them up to the repository root |
| `./pyproject.toml` | the first one found up the tree, `[tool.keycmd]` table |
| `%LOCALAPPDATA%\keycmd\backend` | the remembered keyring backend, on Windows |
| `~/Library/Caches/keycmd/backend` | the remembered keyring backend, on macOS |
| `$XDG_CACHE_HOME/keycmd/backend` | the remembered keyring backend, on Linux (usually `~/.cache`) |

The cache file is safe to delete at any moment; it costs one slower run to write again.

## Exit status

keycmd exits with `1` and a `keycmd: error: ...` message of its own when a configuration is invalid, a command is missing, or there is no keyring backend to read credentials from.

Otherwise the exit status is your command's. On posix, keycmd replaces its own process with the shell, so the status is the shell's directly; on Windows it runs the shell as a subprocess and passes the status along.
