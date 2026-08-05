# Configuration

keycmd is configured with TOML: a `[keys]` table naming the credentials to expose, and an optional `[aliases]` table exposing them again in another shape.

```toml
[keys]
SECRET = { credential = "my-secret", username = "my-username" }
```

For the complete schema, see the [configuration reference](../reference/configuration.md). If a configuration is not doing what you expect, [`keycmd --verbose`](troubleshooting.md) prints every file it loaded and the result of merging them.

## Where configuration lives

Configuration can be stored in three places, where `~` is your home folder and `.` is the working directory you call `keycmd` from:

1. `~/.keycmd`
2. all `.keycmd` files found while walking up the file system from `.`
3. the first `pyproject.toml` found while walking up the file system from `.`

They are loaded and merged in that order, and merged deeply: later sources win per field, so a project can override a single option without restating the whole entry.

!!! note "The search stays inside your project"

    The search for `.keycmd` and `pyproject.toml` stops at the root of a git repository, and before your home folder, so that configuration applies to a subtree of your file system rather than leaking across projects.

This is what makes keycmd convenient for teams: a `.keycmd` file committed to a repository names the credentials the project needs, and each developer only has to have those credentials in their own keyring.

## Keys

Every entry under `[keys]` becomes one environment variable, named after the entry:

```toml
[keys]
MY_TOKEN = { credential = "azure_secret", username = "azure" }
```

`credential` and `username` together identify the credential in your keyring — they are exactly what is handed to `keyring.get_password()`. The password it returns becomes the value of `MY_TOKEN`.

Two optional fields change the value before it is exposed:

* `format` — a format string, applied first
* `b64` — base64 encoding, applied second

## Format strings

A format string lets you preprocess the credential before it is exposed as an environment variable. It is processed with Python's built-in [`str.format`](https://docs.python.org/3/library/stdtypes.html#str.format), so everything that function supports is available to you.

Three variables can be used in the format string:

* `credential`
* `username`
* `password`

So a basic auth header, for example, is a format string and a base64 flag:

```toml
[keys]
MY_TOKEN = { credential = "MY_TOKEN", username = "azure", format = "{username}:{password}", b64 = true }
```

`format` is applied before `b64`, which is what makes that combination produce the value a basic auth header wants.

## Aliases

Aliases expose the same secret in several forms, without a second lookup in your keyring.

For example, you may have a single Personal Access Token for Azure DevOps, and want to use the same token for `pip`, `npm` and the REST API. `pip` wants the token in plain text, `npm` prefers it base64-encoded, and the REST API expects a basic auth header. Aliases make this easy:

```toml
[keys]
MY_TOKEN = { credential = "azure_secret", username = "azure" }

[aliases]
MY_TOKEN_B64 = { key = "MY_TOKEN", b64 = true }
MY_TOKEN_BASICAUTH = { key = "MY_TOKEN", format = "{username}:{password}", b64 = true }
```

An alias names an existing key with `key`, and takes the same `b64` and `format` options as a key does. The keyring is only consulted once, for `MY_TOKEN`; the aliases are derived from what it returned.

## pyproject.toml

Configuration can equally well live in a project's `pyproject.toml`, under the `tool.keycmd` table. The previous example becomes:

```toml
[tool.keycmd.keys]
MY_TOKEN = { credential = "azure_secret", username = "azure" }

[tool.keycmd.aliases]
MY_TOKEN_B64 = { key = "MY_TOKEN", b64 = true }
MY_TOKEN_BASICAUTH = { key = "MY_TOKEN", format = "{username}:{password}", b64 = true }
```

Only the first `pyproject.toml` found on the way up is used, and it is merged last, so it wins over the `.keycmd` files below it.

!!! warning "Configuration holds names, not secrets"

    Nothing you write in a configuration file is a secret: it names a credential and a user, and the password itself stays in your keyring. That is what makes these files safe to commit — and it is worth keeping it that way.
