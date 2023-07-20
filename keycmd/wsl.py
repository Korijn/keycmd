from subprocess import run

from keyring.backend import KeyringBackend

from .logs import error


def call_host_keyring(python, command):
    p = run(
        [python, "-c", f"import keyring; {command}"], shell=False, capture_output=True
    )
    stdout, stderr = p.stdout.decode("utf-8").strip(), p.stderr.decode("utf-8").strip()
    if p.returncode != 0:
        error(f"call to WSL host keyring failed (python path: {python}): {stderr}")
    return stdout


class WslHostKeyring(KeyringBackend):
    priority = 1
    python = "py.exe"

    def set_password(self, servicename, username, password):
        call_host_keyring(
            self.python,
            f"keyring.set_password('{servicename}', '{username}', '{password}')",
        )

    def get_password(self, servicename, username):
        return call_host_keyring(
            self.python, f"print(keyring.get_password('{servicename}', '{username}'))"
        )

    def delete_password(self, servicename, username):
        call_host_keyring(
            self.python, f"keyring.delete_password('{servicename}', '{username}')"
        )
