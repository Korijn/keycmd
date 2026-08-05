# keycmd 🔑

[![CI](https://github.com/Korijn/keycmd/actions/workflows/ci.yml/badge.svg)](https://github.com/Korijn/keycmd/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/keycmd.svg)](https://badge.fury.io/py/keycmd)

**Prefix any command with `keycmd` to source your secrets from the OS keyring**, instead of risky `.env` files (or worse 🙈). Your credentials are exposed as environment variables for exactly one command, and nowhere else.

📖 **[Documentation](https://korijn.github.io/keycmd)** · 📦 **[PyPI](https://pypi.org/project/keycmd/)** · 🚀 **[Quick Start](https://korijn.github.io/keycmd/getting-started/quick-start/)**

Supports Windows, macOS and Linux. Common applications include npm, pip, uv, poetry, docker, docker compose and kubectl.

## Quick start

```bash
uv tool install keycmd
```

Store a credential in your OS keyring, name it in a `.keycmd` file:

```toml
[keys]
OPENAI_API_KEY = { credential = "my-openai-token", username = "your-username" }
```

...and run anything that needs it:

```bash
keycmd 'python my_openai_script.py'
```

The variable exists inside that command, and nowhere else — no `.env` file, no secret pasted into your terminal, nothing left behind afterwards. 😱 → 😌

Continue with the [Quick Start tutorial](https://korijn.github.io/keycmd/getting-started/quick-start/), which walks through storing the credential on each platform.

## Why keycmd?

* **Your secrets stay in the keyring.** The Windows Credential Manager, the macOS keychain and the Linux secret service already exist to keep credentials safe — keycmd reads from them, so a checked-out repository never has to contain a token.
* **Exposed for one command only**, or for a subshell with `keycmd --shell` when you're debugging.
* **Configuration that follows your project**, merged from your home folder, from `.keycmd` files up the directory tree, and from `pyproject.toml`.
* **One credential, many shapes.** Format strings and aliases expose the same secret as plain text, base64, or a basic auth header — whatever each tool insists on.
* **Any keyring backend**, through [keyring](https://github.com/jaraco/keyring), with no special configuration.

## Documentation

Everything lives at **[korijn.github.io/keycmd](https://korijn.github.io/keycmd)**:

* [Installation](https://korijn.github.io/keycmd/getting-started/installation/) — globally, under pyenv, or from WSL
* [Running commands](https://korijn.github.io/keycmd/guide/running-commands/) — the two invocation forms, quoting, subshells
* [Configuration](https://korijn.github.io/keycmd/guide/configuration/) — where it lives, keys, format strings, aliases
* [Keyring backends](https://korijn.github.io/keycmd/guide/keyring-backends/) — third party backends, and keycmd's startup time
* [WSL](https://korijn.github.io/keycmd/guide/wsl/) — reaching the Windows Credential Manager from a distribution
* [Troubleshooting](https://korijn.github.io/keycmd/guide/troubleshooting/) — start with `keycmd --verbose`
* [Examples](https://korijn.github.io/keycmd/examples/openai/) — an OpenAI API key, and one Azure DevOps token shared by poetry, npm and docker compose
* [Reference](https://korijn.github.io/keycmd/reference/cli/) — every flag, environment variable and configuration field

## Contributing

Issues and pull requests are welcome. See [Contributing](https://korijn.github.io/keycmd/development/contributing/) and [Testing](https://korijn.github.io/keycmd/development/testing/) to get set up:

```bash
uv sync
uv run pre-commit install
uv run pytest tests
```

## License

[MIT](LICENSE)
