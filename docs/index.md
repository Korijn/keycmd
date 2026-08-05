# keycmd 🔑

Prefix any command with `keycmd` to source your secrets and credentials from the OS keyring, instead of risky `.env` files (or worse 🙈).

```bash
keycmd npm install
```

That's the whole idea. keycmd looks up the credentials named in your configuration, exposes them as environment variables, and runs your command with them — for the duration of that one command, and nowhere else. Nothing is written to disk, nothing is left behind in your shell history, and no `.env` file has to exist.

It supports Windows, macOS and Linux, and works with npm, pip, uv, poetry, docker, docker compose, kubectl, and anything else that reads a credential from the environment.

## Why keycmd?

* **Your secrets stay in the keyring.** The Windows Credential Manager, the macOS keychain and the Linux secret service already exist to keep credentials safe. keycmd reads from them, so a checked-out repository never has to contain a token.
* **Exposed for one command only.** `keycmd your command` sets the variables for that process and nothing else. There is also `keycmd --shell` for a subshell, when you are debugging something that needs them for a while.
* **Configuration that follows your project.** Configuration is merged from your home folder, from `.keycmd` files up the directory tree, and from `pyproject.toml`, so a project can name the credentials it needs without every developer setting them up by hand.
* **One credential, many shapes.** [Format strings and aliases](guide/configuration.md#format-strings) expose the same secret as plain text, base64, or a basic auth header — whatever each tool insists on.
* **Any keyring backend.** keycmd talks to your OS keyring through [keyring](https://github.com/jaraco/keyring), so every [third party backend](https://github.com/jaraco/keyring/#third-party-backends) works too, with no special configuration.

## A taste of keycmd

Store a credential in your OS keyring, name it in a `.keycmd` file:

```toml
[keys]
OPENAI_API_KEY = { credential = "my-openai-token", username = "your-username" }
```

...and run anything that needs it, by putting `keycmd` in front of the command you were going to run anyway:

```bash
keycmd python my_openai_script.py
keycmd jupyter notebook
```

The variable exists inside those commands, and nowhere else.

## Where to go next

* [Installation](getting-started/installation.md) — install keycmd globally, or under pyenv, or for use from WSL.
* [Quick Start](getting-started/quick-start.md) — store a credential, write a config file, see it work, in a few minutes.
* [Guide](guide/running-commands.md) — running commands, quoting, configuration, keyring backends, WSL and troubleshooting in depth.
* [Examples](examples/openai.md) — an OpenAI API key, and a single Azure DevOps token shared between poetry, npm and docker compose.
* [Reference](reference/cli.md) — every CLI flag, environment variable and configuration field.
