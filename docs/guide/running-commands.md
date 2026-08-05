# Running Commands

There are two ways to use keycmd:

```bash
keycmd your command     # run one command with the credentials exposed
keycmd --shell          # open a subshell with the credentials exposed
```

The first is the preferred one, since your secrets are only exposed as environment variables for the duration of a single command. The second is less preferable, but can be convenient when you are debugging a process that depends on the credentials you are exposing.

## Prefix your command

Write the command the way you would have written it anyway, and put `keycmd` in front of it:

```bash
keycmd npm install
keycmd docker compose up -d
keycmd pytest -k auth --maxfail 1
```

That is the whole idea, and it is all most commands need: the tool you are running reads its credential from the environment itself, and keycmd is what puts it there.

Everything after `keycmd`'s own options belongs to your command, dashes and all. `keycmd pytest --verbose` runs pytest verbosely; it is `keycmd --verbose pytest` that makes *keycmd* verbose.

Each argument is passed on as the word it was, so nothing you typed is split or expanded a second time:

```bash
# arrives as a single argument, spaces and all
keycmd mytool --message 'hello world'
```

The quotes there are your own shell's, doing their usual job. keycmd re-quotes each argument for the shell it hands the command to, so what `mytool` receives is the argv your shell built.

!!! note "Two limits on Windows"

    Both are the platform's rather than keycmd's, and no amount of quoting lifts either. `cmd` reaches a command through the Windows command line, which cannot hold a newline and which expands `%VAR%` inside an argument. Windows PowerShell drops an embedded `"` and an empty argument when it calls a native command; `pwsh` (PowerShell 7.3 and up) does not.

## Ending keycmd's options with `--`

A command whose *first* word starts with a dash would be read as an option of keycmd's. Put `--` in front of it to say that keycmd's own options have ended:

```bash
keycmd -- --my-oddly-named-tool
```

`--` is also simply a habit worth keeping, since every tool that goes on to run another one takes it:

```bash
keycmd -- npm install
```

Only the `--` that ends keycmd's options is removed; any further `--` is your command's own and is passed along untouched.

## A quoted command line

Written as a single quoted argument, the command is handed to your shell as typed, and the shell interprets it — pipes, redirects, globs, `&&` and variable expansion included:

```bash
keycmd 'echo $SECRET | tr a-z A-Z'
keycmd 'npm ci && npm run build'
```

This matters especially for the credentials themselves. `$SECRET` has to be expanded by the shell keycmd starts, because that is the only shell the variable exists in:

```bash
keycmd echo $SECRET    # your own shell expands it, before keycmd sets it — empty
keycmd 'echo $SECRET'  # the shell keycmd starts expands it — correct
```

!!! tip "Which form should I use?"

    Prefix your command as you normally write it, and reach for quotes when you need a shell: pipes, `&&`, redirects, globs, and above all a credential you want expanded into the command line rather than read from the environment.

## A subshell

`keycmd --shell` starts an interactive subshell with the same environment:

```bash
keycmd --shell
```

Every command you run in it has the credentials available, until you exit it. Keep in mind that this means the secrets are in the environment of a long-lived process, and of everything you start from it — which is precisely what the one-off form avoids.

## Which shell keycmd uses

keycmd asks [shellingham](https://github.com/sarugaku/shellingham) which shell invoked it, and falls back on `$SHELL` on posix or `%COMSPEC%` on Windows if that fails. In other words, it runs your command in the shell you were already using — in both forms, which is what lets `keycmd npm install` find the `npm.cmd` on your Windows `PATH`.

On posix, keycmd replaces its own process with the shell (`execvpe`), so it does not sit in the process tree waiting around. Windows has no equivalent, so there keycmd runs the shell as a subprocess and passes its exit code along.

`--verbose` reports what it decided:

```
keycmd: detected shell: C:\Windows\System32\cmd.exe
keycmd: running command: ['C:\\Windows\\System32\\cmd.exe', '/C', 'echo', '%ARTIFACTS_TOKEN_B64%']
```

Under WSL the answer is not a shell at all but `wsl.exe`, which is [its own topic](wsl.md).
