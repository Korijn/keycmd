# Configuration Reference

Configuration is TOML, and lives in `~/.keycmd`, in `.keycmd` files up the directory tree, and in the `[tool.keycmd]` table of a `pyproject.toml`. See [configuration](../guide/configuration.md) for how those are found and merged.

## Schema

* `keys`: dict
    * `{key_name}`: dict — an environment variable will be created with this name
        * `credential`: str — the name of the credential in your keyring
        * `username`: str — the username associated with the credential in your keyring
        * `b64`: bool, optional — set to `true` to apply base64 encoding
        * `format`: str, optional — apply a format string (applied before base64 encoding)
* `aliases`: dict, optional
    * `{alias_name}`: dict — an environment variable will be created with this name
        * `key`: str — the key that should be aliased
        * `b64`: bool, optional — see `keys.{key_name}.b64`
        * `format`: str, optional — see `keys.{key_name}.format`

## Fields

### `keys.{key_name}.credential`

**Required.** The name of the credential in your keyring. Together with `username`, this is what is looked up — they are the two arguments of keyring's `get_password()`. A credential that does not exist is a user error, not an empty variable:

```
keycmd: error: MISSING credential my-secret with user my-username as it does not exist
```

### `keys.{key_name}.username`

**Required.** The username associated with the credential in your keyring. On macOS this is the keychain item's *Account Name*; on Windows it is the *User name* of the generic credential.

### `keys.{key_name}.format`

Optional. A [`str.format`](https://docs.python.org/3/library/stdtypes.html#str.format) format string, applied to the password before it is exposed. Three variables are available: `credential`, `username` and `password`.

```toml
format = "{username}:{password}"
```

### `keys.{key_name}.b64`

Optional, defaults to `false`. Base64-encode the value, *after* `format` has been applied — which is the order that turns `{username}:{password}` into a basic auth value.

### `aliases.{alias_name}.key`

**Required.** The name of an entry under `[keys]` to re-expose. The credential is looked up once, for the key; the alias only applies its own `format` and `b64` to what came back. An alias naming a key that does not exist is an error.

### `aliases.{alias_name}.format`, `aliases.{alias_name}.b64`

Optional, and identical in behaviour to the key fields of the same name. They are not inherited from the aliased key: an alias without them exposes the raw password, regardless of what the key does.

## Examples

A credential exposed as-is:

```toml
[keys]
SECRET = { credential = "my-secret", username = "my-username" }
```

The same credential in three shapes — plain, base64, and basic auth — with one keyring lookup:

```toml
[keys]
MY_TOKEN = { credential = "azure_secret", username = "azure" }

[aliases]
MY_TOKEN_B64 = { key = "MY_TOKEN", b64 = true }
MY_TOKEN_BASICAUTH = { key = "MY_TOKEN", format = "{username}:{password}", b64 = true }
```

The same, in a `pyproject.toml`:

```toml
[tool.keycmd.keys]
MY_TOKEN = { credential = "azure_secret", username = "azure" }

[tool.keycmd.aliases]
MY_TOKEN_B64 = { key = "MY_TOKEN", b64 = true }
MY_TOKEN_BASICAUTH = { key = "MY_TOKEN", format = "{username}:{password}", b64 = true }
```
