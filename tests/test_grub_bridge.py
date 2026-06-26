from unittest.mock import MagicMock

import pytest

from ajustes.core.errors import GrubError
from ajustes.core.grub_bridge import RealGrubBridge


def test_apply_runs_pkexec_install_and_update_grub():
    captured = {}

    def run(args):
        captured["args"] = args
        # el script referencia un temp; léelo para verificar el contenido
        script = args[-1]
        for word in script.split():
            if word.startswith("/") and word.endswith(".tmp") or "/tmp" in word:
                pass
        return MagicMock(returncode=0, stdout="")

    RealGrubBridge(run=run).apply('GRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
    args = captured["args"]
    assert args[0] == "pkexec"
    assert "/etc/default/grub" in args[-1]
    assert "update-grub" in args[-1]


def test_apply_writes_content_to_temp_referenced_in_command(tmp_path):
    seen = {}

    def run(args):
        # extrae la ruta temp del script y lee su contenido en el momento de la llamada
        import re
        m = re.search(r"(\S+grub_ajustes\S*)", args[-1])
        seen["content"] = open(m.group(1)).read() if m else None
        return MagicMock(returncode=0, stdout="")

    RealGrubBridge(run=run).apply("NUEVO_CONTENIDO\n")
    assert seen["content"] == "NUEVO_CONTENIDO\n"


def test_apply_auth_cancelled_raises_friendly():
    bridge = RealGrubBridge(run=lambda a: MagicMock(returncode=126, stdout=""))
    with pytest.raises(GrubError, match="(?i)autenticaci"):
        bridge.apply("x")


def test_apply_nonzero_raises():
    bridge = RealGrubBridge(run=lambda a: MagicMock(returncode=1, stdout="boom"))
    with pytest.raises(GrubError):
        bridge.apply("x")


def test_apply_binary_missing_raises():
    def run(_a):
        raise FileNotFoundError
    with pytest.raises(GrubError):
        RealGrubBridge(run=run).apply("x")
