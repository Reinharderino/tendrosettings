from unittest.mock import MagicMock

import pytest

from ajustes.core.errors import CredentialError
from ajustes.core.gpg_bridge import GpgBridge

COLONS = (
    "sec:u:255:22:ABCDEF1234567890:1700000000:1800000000::u:::scESC:::+::ed25519:::0:\n"
    "fpr:::::::::AAAA:\n"
    "uid:u::::1700000000::H::Name <m@x.com>::::::::::0:\n"
)


def _run(calls, returncode=0, stdout=""):
    def run(args):
        calls.append(args)
        return MagicMock(returncode=returncode, stdout=stdout)
    return run


def test_list_keys_parses():
    keys = GpgBridge(run=_run([], stdout=COLONS)).list_keys()
    assert keys[0].keyid == "ABCDEF1234567890"


def test_list_keys_command():
    calls = []
    GpgBridge(run=_run(calls, stdout=COLONS)).list_keys()
    assert calls[0] == ["gpg", "--list-secret-keys", "--with-colons"]


def test_export_public_returns_stdout():
    out = GpgBridge(run=_run([], stdout="-----BEGIN PGP PUBLIC KEY-----\n")).export_public("ABC")
    assert out.startswith("-----BEGIN PGP PUBLIC KEY-----")


def test_export_public_command():
    calls = []
    GpgBridge(run=_run(calls, stdout="x")).export_public("ABC")
    assert calls[0] == ["gpg", "--armor", "--export", "ABC"]


def test_generate_command():
    calls = []
    GpgBridge(run=_run(calls)).generate("Juan Perez", "j@x.com")
    assert calls[0][:3] == ["gpg", "--batch", "--quick-generate-key"]
    assert "Juan Perez <j@x.com>" in calls[0]


def test_generate_nonzero_raises():
    with pytest.raises(CredentialError):
        GpgBridge(run=_run([], returncode=2, stdout="boom")).generate("A", "a@x.com")


def test_missing_binary_raises():
    def run(_a):
        raise FileNotFoundError
    with pytest.raises(CredentialError):
        GpgBridge(run=run).list_keys()
