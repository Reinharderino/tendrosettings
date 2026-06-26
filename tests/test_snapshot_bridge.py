from unittest.mock import MagicMock

import pytest

from ajustes.core.errors import SnapshotError
from ajustes.core.snapshot_bridge import SnapperBridge


def _run(calls, returncode=0, stdout=""):
    def run(args):
        calls.append(args)
        return MagicMock(returncode=returncode, stdout=stdout)
    return run


def test_create_builds_command_and_returns_number():
    calls = []
    bridge = SnapperBridge(run=_run(calls, stdout="42\n"))
    num = bridge.create_snapshot("mi snapshot")
    assert num == 42
    assert calls[0] == [
        "pkexec", "snapper", "-c", "root", "create",
        "-d", "mi snapshot", "--print-number",
    ]


def test_create_nonzero_raises():
    bridge = SnapperBridge(run=_run([], returncode=1, stdout="err"))
    with pytest.raises(SnapshotError):
        bridge.create_snapshot("x")


def test_create_auth_cancelled_raises_friendly():
    # pkexec devuelve 126 cuando el usuario cancela/deniega la autenticación
    bridge = SnapperBridge(run=_run([], returncode=126))
    with pytest.raises(SnapshotError, match="(?i)autenticaci"):
        bridge.create_snapshot("x")


def test_create_binary_missing_raises():
    def run(_args):
        raise FileNotFoundError
    with pytest.raises(SnapshotError):
        SnapperBridge(run=run).create_snapshot("x")


def test_delete_builds_command_with_all_numbers():
    calls = []
    SnapperBridge(run=_run(calls)).delete_snapshots([97, 98])
    assert calls[0] == ["pkexec", "snapper", "-c", "root", "delete", "97", "98"]


def test_delete_empty_does_nothing():
    calls = []
    SnapperBridge(run=_run(calls)).delete_snapshots([])
    assert calls == []


def test_delete_nonzero_raises():
    bridge = SnapperBridge(run=_run([], returncode=1, stdout="boom"))
    with pytest.raises(SnapshotError):
        bridge.delete_snapshots([5])


def test_custom_config_used():
    calls = []
    SnapperBridge(run=_run(calls), config="home").delete_snapshots([1])
    assert calls[0] == ["pkexec", "snapper", "-c", "home", "delete", "1"]
