# keycmd

[![CI](https://github.com/clinicalgraphics/keycmd/actions/workflows/ci.yml/badge.svg)](https://github.com/clinicalgraphics/keycmd/actions/workflows/ci.yml)
[![PyPI version ](https://badge.fury.io/py/keycmd.svg)
](https://badge.fury.io/py/keycmd)

Prefix any command with `keycmd` to safely source your secrets and credentials from the OS keyring, instead of risky `.env` files (or worse 🙈). Common applications include npm, pip, poetry, docker, docker compose and kubectl!

Supports Windows, macOS and Linux.

## About

The main functionality of `keycmd` is to load secrets from your OS keyring and expose them as environment variables for the duration of a single shell command or alternatively for the lifetime of a subshell.

This enables you to store sensitive data such as authentication tokens and passwords in your OS keyring, so you no longer need to rely on insecure practises such as `.env` files, or pasting secrets into your terminal. 😱

The most common use case is to load credentials for package managers such as pip and npm when using private package indexes, such as Azure Artifact Feeds. Another common use case is docker build secrets.

## Installation

> **Note**
> If you're intending to install `keycmd` in a WSL or pyenv environment, you'll have to skip ahead to the specific installation instructions for those environments.

### Global installation

Install `keycmd` from pypi using `pip install keycmd`, or whatever alternative python package manager you prefer.

Note that the executable `keycmd` has to be installed to a folder that is on your `PATH` environment variable, or the command won't be available globally. Assuming you were able to run `pip` just now, the `keycmd` executable should end up in the exact same location and everything should be fine.

To verify keycmd is installed and available, run `keycmd --version`.

### pyenv installation

Now, if you're using pyenv, you're going to have to jump through a few hoops since keycmd needs to be installed globally, which flies directly into the face of what pyenv is trying to accomplish.

This guide assumes you've also installed [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv), in order to get you the cleanest of setups. ✨

Run the following commands one by one to install keycmd into its own standalone environment:

```bash
# run the following commands one by one
pyenv virtualenv 3.9 keycmd
pyenv activate keycmd
pip install keycmd
pathToKeycmd=$(python -c 'import sys; from pathlib import Path; print(Path(sys.executable).parent / "keycmd")')
pyenv deactivate
mkdir -p $HOME/.local/bin
ln -s $pathToKeycmd $HOME/.local/bin/keycmd
```

Finally, edit your `~/.bashrc` file (or whatever shell profile you use) to include `~/.local/bin` in your `PATH` variable:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

> **Note**
> This line already be in place in your `~/.bashrc`, for example if you installed poetry, since it's a common trick used to expose specific binaries on `PATH` when they are in folders with other binaries that you do _not_ want to expose on `PATH`.

To verify keycmd is installed and available, run `keycmd --version`.

### WSL installation

First, you have to install keycmd according to the above instructions (globally, or with pyenv). Then, there's some additional setup to take care of...

If you're using WSL, you'll run into a wall when you first try to use keycmd. That's because keycmd uses the keyring library to connect to OS keyrings, and keyring will attempt to connect to your linux distro's (probably Ubuntu) keyring background service, which by default isn't actually running in a WSL environment!

If you did actually set up your linux distro's keyring background service, that's fine, you can continue using it and don't need to perform any additional steps.

However, if you would like keyring to connect from the WSL environment to your Windows Credential Manager instead, you can install [keyring-pybridge](https://github.com/ClinicalGraphics/keyring-pybridge) in the same python environment where you installed `keycmd`. Please refer to the [installation instructions for WSL](https://github.com/ClinicalGraphics/keyring-pybridge#installation).

## Quickstart

Now that keycmd is installed, we can perform a quick test to see how it works!

Let's add a new key to our OS keyring, and then see how we can expose it with keycmd.

For the purpose of this example, use `my-secret` as the credential name and `my-username` as the... username. I used `foobar` as the password.

On Windows, that means clicking Start and typing "Credential Manager" to find the app. Click the Windows Credentials tab, and click "Add a generic credential". See the screenshots below.

![Credential Manager](docs/wcm.png)

![Add Key](docs/wcm-add-key.png)

> **Note**
> Pull requests to add visual guides for other platforms are most welcome!

Now, create a `.keycmd` config file in your user home folder. Put the following configuration in the file and save:

```toml
[keys]
SECRET = { credential = "my-secret", username = "my-username" }
```

Finally, open a terminal and run a command to print the secret, so we can see if it worked. That's going to look different depending on what shell you're using, so here's a couple examples:

* Cmd: `keycmd echo %SECRET%`
* Powershell: `keycmd 'echo $env:SECRET'`
* Bash: `keycmd 'echo $SECRET'`

You should see the text `foobar` being printed to the terminal.

You've successfully set up keycmd! 👏

See the [advanced configuration example](#advanced-example) below for a more involved usecase for keycmd, where poetry, npm and docker-compose are all put together.

## Usage

The CLI has the following options:

```
❯ keycmd --help
usage: keycmd [-h] [-v] [--version] [--shell] ...

positional arguments:
  command        command to run

optional arguments:
  -h, --help     show this help message and exit
  -v, --verbose  enable verbose output, useful for configuration debugging
  --version      print version info
  --shell        spawn a subshell instead of running a command
```

There are two main ways to use the CLI:

* `keycmd ...`
* `keycmd --shell`

The first is the most preferred method, since your secrets will only be exposed as environment variables during a one-off command. The latter is less preferable, but can be convenient if you are debugging some process that depends on the credentials you are exposing.

## Configuration

> **Note**
> if you are having trouble configuring keycmd, refer to section [debugging configuration](#debugging-configuration).

### Locations

Configuration can be stored in three places (where `~` is the user home folder and `.` is the current working directory when calling `keycmd`):

- `~/.keycmd`
- first `pyproject.toml` found while walking file system up from `.`
- `./.keycmd`

Configuration files are loaded and merged in the listed order.

### Options

The options are a nested dictionary, defined as follows:

* `keys`: dict
  * `{key_name}`: dict
    * `credential`: str
    * `username`: str
    * `b64`: bool, optional

You can define as many keys as you like. For each key, you are required to define:

* the `key_name`, which is the name of the environment variable under which the credential will be exposed
* the `credential`, which is the name of the credential in your OS keyring
* the `username`, which is the name of the user owning the credential in the OS keyring

Optionally, you can also set `b64` to `true` to apply base64 encoding to the credential.

## Advanced example

This is an example configuration for Poetry, npm and docker-compose. It should inspire you to see the possibilities keycmd provides thanks to its configuration system.

In this example, I've stored the following configuration in `~/.keycmd`:

```toml
[keys]
ARTIFACTS_TOKEN = { credential = "korijn@poetry-repository-main", username = "korijn" }
ARTIFACTS_TOKEN_B64 = { credential = "korijn@poetry-repository-main", username = "korijn", b64 = true }
```

This configuration piggybacks off of the credentials created in the OS keyring by [Poetry](https://python-poetry.org/) when [configuring credentials](https://python-poetry.org/docs/repositories/#configuring-credentials) for a private repository. In this case, the same credential is exposed twice:

* As the environment variable `ARTIFACTS_TOKEN`
* Again but with base64 encoding applied as the environment variable `ARTIFACTS_TOKEN_B64`

For my npm project, I have a [`.npmrc` file](https://docs.npmjs.com/cli/v7/configuring-npm/npmrc) with the following contents:

```
registry=https://pkgs.dev.azure.com/my_organization/_packaging/main/npm/registry/
always-auth=true
//pkgs.dev.azure.com/my_organization/_packaging/main/npm/registry/:username=dev
//pkgs.dev.azure.com/my_organization/_packaging/main/npm/registry/:_password=${ARTIFACTS_TOKEN_B64}
//pkgs.dev.azure.com/my_organization/_packaging/main/npm/registry/:email=email
//pkgs.dev.azure.com/my_organization/_packaging/main/npm/:username=dev
//pkgs.dev.azure.com/my_organization/_packaging/main/npm/:_password=${ARTIFACTS_TOKEN_B64}
//pkgs.dev.azure.com/my_organization/_packaging/main/npm/:email=email
```

Now, I can set up my `node_modules` just by calling `keycmd npm install`! 🚀

> **Note**
> npm will complain if you make any calls such as `npm run [...]` without the environment variable set. 🙄 You can set them to the empty string to make npm shut up. I use `export ARTIFACTS_TOKEN_B64=` (or `setx ARTIFACTS_TOKEN_B64=` on Windows).

Additionally, I also have a docker-compose file in this project which is configured as follows:

```yml
secrets:
  token:
    environment: ARTIFACTS_TOKEN
  token_b64:
    environment: ARTIFACTS_TOKEN_B64
```

When I call `keycmd docker compose build` these two variables are exposed by keycmd and subsequently they are available as [docker compose build secrets](https://docs.docker.com/compose/use-secrets/). 👌

## Debugging configuration

If you're not getting the results you expected, use the `-v` flag
to debug your configuration.

```
❯ poetry run keycmd -v echo %ARTIFACTS_TOKEN_B64%
keycmd: loading config file C:\Users\kvang\.keycmd
keycmd: loading config file C:\Users\kvang\dev\keycmd\pyproject.toml
keycmd: merged config:
{'keys': {'ARTIFACTS_TOKEN': {'credential': 'korijn@poetry-repository-main',
                              'username': 'korijn'},
          'ARTIFACTS_TOKEN_B64': {'b64': True,
                                  'credential': 'korijn@poetry-repository-main',
                                  'username': 'korijn'}}}
keycmd: exposing credential korijn@poetry-repository-main belonging to user korijn as environment variable ARTIFACTS_TOKEN (b64: False)
keycmd: exposing credential korijn@poetry-repository-main belonging to user korijn as environment variable ARTIFACTS_TOKEN_B64 (b64: True)
keycmd: detected shell: C:\Windows\System32\cmd.exe
keycmd: running command: ['C:\\Windows\\System32\\cmd.exe', '/C', 'echo', '%ARTIFACTS_TOKEN_B64%']
aSdtIG5vdCB0aGF0IHN0dXBpZCA6KQ==
```

## Note on keyring backends

Since keycmd uses keyring as its backend, you're not limited to just working with OS keyrings. 🤯 Any keyring backend will work with keycmd. No special configuration required!

See the [third party backends](https://github.com/jaraco/keyring/#third-party-backends) list for all options.
