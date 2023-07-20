# keycmd

## Configuration

Configuration can be stored in three places:

- `~/.keycmd`
- `./.keycmd`
- first `pyproject.toml` found while walking file system up from `.`

Configuration is merged where more local configuration values have precendence.

Example `.keycmd` configuration:

```toml
[keys]  # use [tool.keycmd.keys] in a pyproject.toml file
ARTIFACTS_TOKEN = { credential = "azure@poetry-repository-main", username = "azure" }
ARTIFACTS_TOKEN_B64 = { credential = "azure@poetry-repository-main", username = "azure", b64 = true }
```

## CLI

This package installs the following cli tool:

```sh
❯ keycmd --help
usage: keycmd [-h] [-v] [--version] [--shell] [command ...]

positional arguments:
  command        command to run

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  enable verbose output, useful for configuration debugging
  --version      print version info
  --shell        spawn a subshell instead of running a command
```

The configured credentials will be loaded from the OS keyring only for the duration of the subprocesses.
