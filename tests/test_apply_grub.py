from unittest.mock import MagicMock

from ajustes.core.apply_grub import ApplyGrub

GRUB = """GRUB_TIMEOUT=5
GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3"
GRUB_DISABLE_OS_PROBER=false
"""


def _make(tmp_path):
    grub = tmp_path / "grub"
    grub.write_text(GRUB, encoding="utf-8")
    backups = tmp_path / "backups"
    bridge = MagicMock()
    return ApplyGrub(bridge=bridge, default_grub_path=grub, backups_dir=backups), bridge, grub, backups


def test_backs_up_current_file(tmp_path):
    apply, _, _, backups = _make(tmp_path)
    apply.execute("quiet splash")
    saved = list(backups.glob("grub.*"))
    assert saved and 'GRUB_CMDLINE_LINUX_DEFAULT="quiet loglevel=3"' in saved[0].read_text()


def test_bridge_receives_replaced_content(tmp_path):
    apply, bridge, _, _ = _make(tmp_path)
    apply.execute("quiet splash mitigations=off")
    content = bridge.apply.call_args.args[0]
    assert 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash mitigations=off"' in content
    assert "GRUB_TIMEOUT=5" in content                 # preserva resto
    assert "GRUB_DISABLE_OS_PROBER=false" in content
    assert content.count("GRUB_CMDLINE_LINUX_DEFAULT=") == 1


def test_does_not_write_grub_file_directly(tmp_path):
    # la escritura privilegiada es responsabilidad del bridge; el fichero real no cambia aquí
    apply, _, grub, _ = _make(tmp_path)
    apply.execute("quiet")
    assert grub.read_text() == GRUB
