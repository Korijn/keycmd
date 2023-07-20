# keycmd

The purpose of `keycmd` is to load secrets from your OS keyring and expose them as environment variables for a limited amount of time, to minimize exposure and security risk.

A limited amount of time here means only during a single shell command or alternatively for the lifetime of a subshell.

The most common use case is to load credentials for package managers such as pip, npm when using private package indexes, such as Azure Artifact Feeds. Another common use case is docker build secrets, also when connecting to servuces that require authentication with passwords or tokens.

## Configuration

Configuration can be stored in three places (where `~` is the user home folder and `.` is the current working directory when calling `keycmd`):

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

## Verbose output

If you're not getting the results you expected, use the `-v` flag
to debug your configuration. For example:

```sh
❯ poetry run keycmd -v echo %ARTIFACTS_TOKEN_B64%
keycmd: loading config file C:\Users\kvang\.keycmd
keycmd: loading config file C:\Users\kvang\dev\keycmd\pyproject.toml
keycmd: merged config:
{'keys': {'ARTIFACTS_TOKEN': {'credential': 'azure@poetry-repository-main',
                              'username': 'azure'},
          'ARTIFACTS_TOKEN_B64': {'b64': True,
                                  'credential': 'azure@poetry-repository-main',
                                  'username': 'azure'}}}
keycmd: exposing credential azure@poetry-repository-main belonging to user azure as environment variable ARTIFACTS_TOKEN
keycmd: exposing credential azure@poetry-repository-main belonging to user azure as environment variable ARTIFACTS_TOKEN_B64
keycmd: detected shell: C:\Windows\System32\cmd.exe
keycmd: running command: ['C:\\Windows\\System32\\cmd.exe', '/C', 'echo', '%ARTIFACTS_TOKEN_B64%']
aSdtIG5vdCB0aGF0IHN0dXBpZCA6KQ==
```
