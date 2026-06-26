from unittest.mock import MagicMock

import pytest

from ajustes.core.errors import CredentialError
from ajustes.core.tls_bridge import TlsBridge

TRUST = """pkcs11:id=%ab;type=cert
    type: certificate
    label: Root CA
    trust: anchor
    category: authority
"""


def _run(calls, returncode=0, stdout=""):
    def run(args):
        calls.append(args)
        return MagicMock(returncode=returncode, stdout=stdout)
    return run


def test_list_cas_parses():
    cas = TlsBridge(run=_run([], stdout=TRUST)).list_cas()
    assert cas[0].label == "Root CA"


def test_list_cas_command():
    calls = []
    TlsBridge(run=_run(calls, stdout=TRUST)).list_cas()
    assert calls[0] == ["trust", "list"]


def test_add_anchor_command():
    calls = []
    TlsBridge(run=_run(calls)).add_anchor("/tmp/my-ca.crt")
    assert calls[0] == ["pkexec", "trust", "anchor", "/tmp/my-ca.crt"]


def test_remove_anchor_command():
    calls = []
    TlsBridge(run=_run(calls)).remove_anchor("pkcs11:id=%ab;type=cert")
    assert calls[0] == ["pkexec", "trust", "anchor", "--remove", "pkcs11:id=%ab;type=cert"]


def test_add_anchor_auth_cancelled_raises():
    with pytest.raises(CredentialError, match="(?i)autenticaci"):
        TlsBridge(run=_run([], returncode=126)).add_anchor("/tmp/x.crt")


def test_missing_binary_raises():
    def run(_a):
        raise FileNotFoundError
    with pytest.raises(CredentialError):
        TlsBridge(run=run).list_cas()
