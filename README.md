# keyring-tools

## Configuration

Configuration can be stored in three places:

- `~/.keyring-tools`
- `./.keyring-tools`
- first `pyproject.toml` found while walking file system up from `.`

Configuration is merged where more local configuration values have precendence.

Example `.keyring-tools` configuration:

```toml
[keys]  # use [tool.keyring-tools.keys] in a pyproject.toml file
ARTIFACTS_TOKEN = { credential = "azure@poetry-repository-main", username = "azure" }
ARTIFACTS_TOKEN_B64 = { credential = "azure@poetry-repository-main", username = "azure", b64 = true }
```

## Commands

This package installs two command line applications:

- `keyring-cmd ...` to run a one-off command
- `keyring-shell` to spawn a subshell

The configured credentials will be loaded from the OS keyring only for the duration of the subprocesses.

## About

Run `keyring-tools` to print the version.
