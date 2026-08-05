# Running Commands

There are two ways to use keycmd:

```bash
keycmd 'your command'   # run one command with the credentials exposed
keycmd --shell          # open a subshell with the credentials exposed
```

The first is the preferred one, since your secrets are only exposed as environment variables for the duration of a single command. The second is less preferable, but can be convenient when you are debugging a process that depends on the credentials you are exposing.

## One command

In its most common form, keycmd takes the command to run as a single quoted argument:

```bash
keycmd 'npm install'
```

Quoting the whole command as one argument is what lets you use your shell's syntax inside it:

```bash
keycmd 'echo $SECRET | tr a-z A-Z'
```

keycmd hands that line to your shell exactly as you typed it, and your shell does the rest — pipes, redirects, variable expansion and all. This matters especially for the credentials themselves: `$SECRET` has to be expanded by the shell keycmd starts, because that is the only shell the variable exists in.

## Separate arguments

You can also write the command out as separate arguments, and then keycmd keeps them separate:

```bash
# arrives as a single argument, spaces and all
keycmd mytool --message 'hello world'
```

Since each argument is passed on as the word it was, your shell's syntax is *not* interpreted a second time in this form. If you want `$SECRET` expanded, either let your own shell expand it, or use the single argument form above.

!!! tip "Which form should I use?"

    Use the quoted form for anything that needs a shell: pipes, `&&`, redirects, globs, and above all the credentials you came here for. Use separate arguments when you are passing along text that must survive untouched, such as an argument that itself contains `$` or quotes.

## A subshell

`keycmd --shell` starts an interactive subshell with the same environment:

```bash
keycmd --shell
```

Every command you run in it has the credentials available, until you exit it. Keep in mind that this means the secrets are in the environment of a long-lived process, and of everything you start from it — which is precisely what the one-off form avoids.

## Which shell keycmd uses

keycmd asks [shellingham](https://github.com/sarugaku/shellingham) which shell invoked it, and falls back on `$SHELL` on posix or `%COMSPEC%` on Windows if that fails. In other words, it runs your command in the shell you were already using.

On posix, keycmd replaces its own process with the shell (`execvpe`), so it does not sit in the process tree waiting around. Windows has no equivalent, so there keycmd runs the shell as a subprocess and passes its exit code along.

`--verbose` reports what it decided:

```
keycmd: detected shell: C:\Windows\System32\cmd.exe
keycmd: running command: ['C:\\Windows\\System32\\cmd.exe', '/C', 'echo', '%ARTIFACTS_TOKEN_B64%']
```

Under WSL the answer is not a shell at all but `wsl.exe`, which is [its own topic](wsl.md).
