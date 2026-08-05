"""Reaching the Windows credential manager from a WSL shell

The docs tell WSL users to install keycmd on Windows and call it from
their WSL shell, so that keyring talks to the Windows credential manager
instead of a keyring daemon inside the distro. These tests walk that path
end to end: a credential in the credential manager, a shell inside WSL,
and the Windows install of keycmd in between.

They run on any Windows machine with a distribution that answers, and
skip themselves with the reason anywhere else; the `wsl` fixture in
conftest.py works out which of the two it is, and KEYCMD_REQUIRE_WSL=1
turns that skip into a failure, which is what the CI job that installs
WSL sets.
"""


def test_wsl_reads_windows_paths(wsl, tmp_path):
    """WSL is reachable, and it sees the Windows file system where expected"""
    marker = tmp_path / "marker"
    marker.write_text("hello from windows", encoding="utf-8")
    p = wsl.sh(f"cat {wsl.path(marker)}")
    assert p.status == 0, p.output
    assert p.stdout.strip() == "hello from windows"


def test_version_from_wsl(wsl):
    """The Windows install runs when it is invoked from a WSL shell"""
    p = wsl.sh(f"{wsl.keycmd} --version")
    assert p.status == 0, p.output
    assert p.stdout.strip().startswith("keycmd: v")


def test_credential_manager_from_wsl(wsl, ch_tmpdir, local_conf, shell_credentials):
    """A credential stored on Windows reaches a command run from WSL

    The command runs back inside the distribution the user typed it in,
    rather than in a Windows shell: printenv is a Linux command, and the
    credential only reaches it because keycmd shares it through WSLENV.
    """
    var = local_conf.varname
    # one line and free of quotes, so that the script survives the trip
    # through wsl.exe intact; the config is picked up from the working
    # directory, which crosses the boundary as a windows path
    script = f"cd {wsl.path(ch_tmpdir)}; {wsl.keycmd} --verbose printenv {var}"
    p = wsl.sh(script)
    assert p.status == 0, p.output
    assert f"as environment variable {var}" in p.output
    assert "called from WSL" in p.output
    assert shell_credentials.password in p.stdout
