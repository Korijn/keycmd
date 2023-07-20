from pathlib import Path

import keyring
from keyring.backend import KeyringBackend


def is_wsl():
    p = Path("/proc/version")
    if not p.is_file():
        return False
    if "WSL2" in p.read_text():
        return True
    return False


class TestKeyring(KeyringBackend):
    """A test keyring which always outputs the same password
    """
    priority = 1

    def set_password(self, servicename, username, password):
        pass

    def get_password(self, servicename, username):
        password = "sdfsdf"
        print(password)

    def delete_password(self, servicename, username):
        pass


def maybe_use_wsl_keyring():
    if not is_wsl():
        return
    keyring.set_keyring(TestKeyring())
