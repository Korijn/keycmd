# WSL

If you're using WSL, you'll run into a wall the first time you try to use keycmd. That's because keycmd uses the keyring library to connect to OS keyrings, and keyring will attempt to connect to your Linux distribution's (probably Ubuntu) keyring background service, which by default isn't actually running in a WSL environment.

There are two ways out of that, and which one you want depends on what you'd rather maintain.

!!! note "Are you actually working in WSL?"

    Just because you installed WSL on your system does not mean you are working in it. Think about this for a moment: are you using Python from Windows, or from WSL? This page is only relevant if you are actually working inside a distribution.

## Option 1: run a keyring daemon in the distribution

If you did set up your Linux distribution's keyring background service, that's fine — you can keep using it and don't need any of the steps below. Inside the distribution keycmd is then an ordinary posix process talking to an ordinary posix keyring, and everything on the rest of this site applies unchanged.

## Option 2: reach the Windows Credential Manager

If you would rather have keyring connect from the WSL environment to your Windows Credential Manager, install keycmd according to the [installation instructions](../getting-started/installation.md) **in Windows**, not in WSL. Then, assuming `keycmd` is on your Windows `PATH`, it should now be available in WSL as well.

That leaves you with one keyring to maintain instead of two, and it is the one your Windows tools already use.

## How keycmd crosses the boundary

Keep in mind that keycmd is a Windows process in this setup, so left to its own devices it would run your command in a Windows shell, and `keycmd --shell` would open one. It doesn't: when keycmd notices it was called from a distribution, it runs your command back inside that distribution through `wsl.exe`, and `keycmd --shell` opens a shell there.

keycmd works out where it was called from by looking at its own process tree and working directory:

* a `wsl.exe` or `wslhost.exe` ancestor means it was called from a distribution
* a Windows shell (`cmd`, `powershell`, `pwsh`) found first means it was called from Windows after all
* failing both, a UNC working directory (`\\wsl$\...` or `\\wsl.localhost\...`) settles it

If you have more than one distribution installed, and you are working somewhere on the distribution's own file system, that working directory also names the distribution, and keycmd passes it to `wsl.exe` as `--distribution`, so your command goes to the distribution you are in rather than the default one.

!!! warning "Quotes do not survive the crossing"

    `wsl.exe` strips the quotes from its own command line before the distribution's shell ever sees it, so an argument containing spaces arrives as several words no matter how it is written. `keycmd npm install` is unaffected, and so is anything else without spaces inside an argument; `keycmd mytool --message 'hello world'` is not, and there is nothing keycmd can do about it from the Windows side.

## Your credentials have to be told to cross

Your credentials do not come along by themselves, since neither side of the WSL boundary inherits the other's environment. Only the variables listed in [`WSLENV`](https://devblogs.microsoft.com/commandline/share-environment-vars-between-wsl-and-windows/) make the trip, so keycmd adds the variables from your configuration to it. Anything you had already listed in `WSLENV` yourself is kept.

## When keycmd gets it wrong

Set the `KEYCMD_WSL` environment variable to override the decision in either direction:

```bash
KEYCMD_WSL=0 keycmd npm install   # stay on the windows side
KEYCMD_WSL=1 keycmd npm install   # go through wsl.exe regardless
```

`keycmd --verbose` reports which way it went, and what it based that on:

```
keycmd: windows process tree: keycmd <- wsl <- svchost
keycmd: called from WSL, by way of wsl
keycmd: sharing with WSL as WSLENV=SECRET
```
