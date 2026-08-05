# Keyring Backends

keycmd reads credentials through [keyring](https://github.com/jaraco/keyring), so you're not limited to just the OS keyrings. 🤯 Any keyring backend works with keycmd, and no special configuration is required.

See keyring's [third party backends](https://github.com/jaraco/keyring/#third-party-backends) list for all the options.

## Startup time

keycmd sits in front of every command you run through it, so its own startup is latency you pay each time.

Left to itself, keyring works out which backend to use by loading every backend registered by every installed package and picking the most suitable one. That search runs on each `keycmd` invocation and, on a machine with a few packages installed, costs more time than the whole of the rest of a `keycmd` run put together.

The answer, though, is the same every time until the packages on your machine change. So keycmd writes it down the first time it needs a credential, and loads that backend by name on every run after, which on the machine this was measured on takes a run from 0.156s to 0.085s. There is nothing to configure and nothing to read; it just gets faster after the first run.

You can watch it happen with `--verbose`, which says where the backend came from:

```
keycmd: keyring backend: keyring.backends.SecretService.Keyring (found in 0.12s)   # the first run
keycmd: keyring backend: keyring.backends.SecretService.Keyring (remembered)       # every run after
```

The note lives with the rest of your cached files, and deleting it costs you nothing but one slow run:

| Platform | Location |
| --- | --- |
| Windows | `%LOCALAPPDATA%\keycmd\backend` |
| macOS | `~/Library/Caches/keycmd/backend` |
| Linux | `$XDG_CACHE_HOME/keycmd/backend` (usually `~/.cache`) |

## When the note goes stale

keycmd only trusts the note as far as it can check it. If the backend it names has been uninstalled, or is no longer usable because the daemon behind it is not running, the run searches again and writes down what it finds instead.

What keycmd cannot notice by itself is a backend that still loads but is no longer the one you want — you installed a better one, or removed a package and want the runner-up. That is what these two flags are for:

```bash
keycmd --detect-backend   # search now, and remember what turns up
keycmd --reset-backend    # forget it, so the next run searches again
```

```
❯ keycmd --detect-backend
keycmd: remembered keyring backend keyring.backends.SecretService.Keyring, found in 0.12s
```

Neither flag needs a configuration or a command: they are about the keyring itself, and return before keycmd looks at anything else.

## Choosing the backend yourself

If you would rather take the whole thing into your own hands, keyring's own `PYTHON_KEYRING_BACKEND` still works, and outranks anything keycmd remembers:

```bash
# in your shell profile; use the backend your platform actually uses
export PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring
```

`keyring --list-backends` prints the names to choose from. The setting is keyring's own, so it applies to everything else using keyring too, and with it set keycmd has nothing to remember — and says so if you ask it to:

```
❯ keycmd --detect-backend
keycmd: PYTHON_KEYRING_BACKEND=keyring.backends.SecretService.Keyring already names the backend to use
```

## No backend at all

If keyring finds no backend it can use, there is nowhere for keycmd to read credentials from, and it says so rather than failing on the first lookup:

```
❯ keycmd 'npm install'
keycmd: error: keyring has no backend to read credentials from
keycmd: hint: install one for this platform, or name one you have with PYTHON_KEYRING_BACKEND
keycmd: hint: see https://github.com/jaraco/keyring#third-party-backends
```

Inside a WSL distribution this usually means the distro's keyring daemon is not running, which is what the [WSL guide](wsl.md) is for; keycmd points you there when it notices it is running in one. Nothing is written down in this case, so there is nothing to reset once you have fixed it.
