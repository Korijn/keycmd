# Troubleshooting

If you're not getting the results you expected, use the `-v` (`--verbose`) flag. keycmd will verbosely tell you about all the steps it's taking, and that is almost always enough to see what went wrong.

## Debugging your configuration

```
❯ keycmd -v echo %ARTIFACTS_TOKEN_B64%
keycmd: loading config file C:\Users\kvang\.keycmd
keycmd: loading config file C:\Users\kvang\dev\keycmd\pyproject.toml
keycmd: merged config:
{'keys': {'ARTIFACTS_TOKEN': {'credential': 'korijn@poetry-repository-main',
                              'username': 'korijn'},
          'ARTIFACTS_TOKEN_B64': {'b64': True,
                                  'credential': 'korijn@poetry-repository-main',
                                  'username': 'korijn'}}}
keycmd: keyring backend: <keyring.backends.Windows.WinVaultKeyring object at 0x000001F8C2A1B4D0> (remembered)
keycmd: exposing credential korijn@poetry-repository-main with user korijn as environment variable ARTIFACTS_TOKEN (b64: False, format: None)
keycmd: exposing credential korijn@poetry-repository-main with user korijn as environment variable ARTIFACTS_TOKEN_B64 (b64: True, format: None)
keycmd: detected shell: C:\Windows\System32\cmd.exe
keycmd: running command: ['C:\\Windows\\System32\\cmd.exe', '/C', 'echo', '%ARTIFACTS_TOKEN_B64%']
aSdtIG5vdCB0aGF0IHN0dXBpZCA6KQ==
```

That output answers, in order, the four questions a misbehaving run usually comes down to:

* **Which files were loaded?** If the file you have been editing is not in the list, it is not where keycmd looks. See [where configuration lives](configuration.md#where-configuration-lives) — the search stops at the root of a git repository and before your home folder.
* **What did they merge into?** The merged configuration is the one that counts, and a value you expected can be overridden by a file loaded later.
* **Which backend answered?** See [keyring backends](keyring-backends.md).
* **What was actually run?** Including the shell, and the exact argument vector handed to it.

The example above echoes a variable, which is why the command is written out for `cmd.exe` rather than prefixed the usual way; in bash or PowerShell it would be quoted as one argument, as in `keycmd -v 'echo $ARTIFACTS_TOKEN_B64'`. See [running commands](running-commands.md).

## Common problems

### `keycmd: command not found`

The executable is not on your `PATH`. See [installation](../getting-started/installation.md) — `uv tool install` and `pipx` handle this for you; a plain `pip install` into some environment may not.

### `keycmd: error: missing command argument`

keycmd was called with no command to run. Either pass one, or use `keycmd --shell` for a subshell.

### The variable is empty, or my shell expanded it before keycmd ran

```bash
keycmd echo $SECRET    # your shell expands $SECRET — before keycmd sets it
keycmd 'echo $SECRET'  # the shell keycmd starts expands it — correct
```

Quote the whole command, so that the shell keycmd starts is the one interpreting it. This only comes up when you write the credential into the command line yourself; a tool that reads it from its own environment needs nothing but `keycmd` in front of it. See [running commands](running-commands.md).

### `sh: --: invalid option`, or `--: command not found`

Your keycmd is old enough to pass a leading `--` on to the shell as the first word of the command. Upgrade, or leave the `--` out — `keycmd npm install` works on every version.

### keycmd took my command's `--verbose` (or `--version`, or `-v`)

Only the options *before* your command are keycmd's; everything from the first word of the command onwards is passed on untouched. `keycmd --verbose pytest` makes keycmd verbose, `keycmd pytest --verbose` makes pytest verbose. If the command's own name starts with a dash, put `--` in front of it.

### `keycmd: error: keyring has no backend to read credentials from`

keyring found nothing on this machine that it can read credentials from. Install a backend for your platform, or name one with `PYTHON_KEYRING_BACKEND`; see [keyring backends](keyring-backends.md). Inside a WSL distribution this usually means no keyring daemon is running — see the [WSL guide](wsl.md).

### `keycmd: error: MISSING credential ... as it does not exist`

The lookup is by credential name *and* username, and both have to match exactly. Check the verbose output for the `exposing credential ... with user ...` line and compare it with what your credential manager shows. On Linux, a password added through a GUI often has no username at all, which is why the [quick start](../getting-started/quick-start.md) sets it through Python's `keyring` package instead.

### `keycmd: error: MISSING alias key ...`

An entry under `[aliases]` names a `key` that no entry under `[keys]` defines. Remember that the merged configuration is what counts: an alias in one file can refer to a key that another file was supposed to provide. See [aliases](configuration.md#aliases).

### npm complains about a missing variable on commands I don't prefix

npm will complain if you make calls such as `npm run [...]` without the environment variable set. 🙄 You can set them to the empty string to make npm shut up: `export PAT_B64=` (or `setx PAT_B64=` on Windows).

### A TOML syntax error

```
keycmd: error: Expected '=' after a key in a key/value pair (at line 3, column 5)
```

One of your configuration files is not valid TOML. The message names the line and column; the file is the last one listed as loading in the verbose output.
