from unittest.mock import MagicMock

import pytest

from ajustes.core.dualboot_bridge import EfibootmgrBridge
from ajustes.core.errors import DualBootError

SAMPLE = """BootCurrent: 0001
BootOrder: 0001,0000
Boot0000* Windows Boot Manager\tHD(2)
Boot0001* Garuda\tHD(2)
"""


def _run(calls, returncode=0, stdout=""):
    def run(args):
        calls.append(args)
        return MagicMock(returncode=returncode, stdout=stdout)
    return run


def test_read_state_runs_efibootmgr_without_pkexec_and_parses():
    calls = []
    state = EfibootmgrBridge(run=_run(calls, stdout=SAMPLE)).read_state()
    assert calls[0] == ["efibootmgr"]
    assert state.current == "0001"
    assert {e.label for e in state.entries} == {"Windows Boot Manager", "Garuda"}


def test_read_state_nonzero_raises():
    with pytest.raises(DualBootError):
        EfibootmgrBridge(run=_run([], returncode=1)).read_state()


def test_read_state_missing_binary_raises():
    def run(_a):
        raise FileNotFoundError
    with pytest.raises(DualBootError):
        EfibootmgrBridge(run=run).read_state()


def test_set_boot_next_command():
    calls = []
    EfibootmgrBridge(run=_run(calls)).set_boot_next("0000")
    assert calls[0] == ["pkexec", "efibootmgr", "--bootnext", "0000"]


def test_set_boot_next_auth_cancelled_raises_friendly():
    bridge = EfibootmgrBridge(run=_run([], returncode=126))
    with pytest.raises(DualBootError, match="(?i)autenticaci"):
        bridge.set_boot_next("0000")


def test_set_boot_order_command():
    calls = []
    EfibootmgrBridge(run=_run(calls)).set_boot_order(["0000", "0001", "0005"])
    assert calls[0] == ["pkexec", "efibootmgr", "--bootorder", "0000,0001,0005"]


def test_set_boot_order_empty_does_nothing():
    calls = []
    EfibootmgrBridge(run=_run(calls)).set_boot_order([])
    assert calls == []


def test_reboot_command():
    calls = []
    EfibootmgrBridge(run=_run(calls)).reboot()
    assert calls[0] == ["systemctl", "reboot"]
