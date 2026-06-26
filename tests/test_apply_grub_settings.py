from unittest.mock import MagicMock

from ajustes.core.apply_grub_settings import ApplyGrubSettings

GRUB = """GRUB_DEFAULT="1>6"
GRUB_TIMEOUT=5
GRUB_DISABLE_OS_PROBER=false
"""


def _make(tmp_path):
    grub = tmp_path / "grub"
    grub.write_text(GRUB, encoding="utf-8")
    bridge = MagicMock()
    return ApplyGrubSettings(bridge=bridge, default_grub_path=grub,
                             backups_dir=tmp_path / "backups"), bridge, grub


def test_applies_multiple_keys_to_bridge(tmp_path):
    apply, bridge, _ = _make(tmp_path)
    apply.execute({"GRUB_TIMEOUT": "10", "GRUB_DISABLE_OS_PROBER": "true"})
    content = bridge.apply.call_args.args[0]
    assert "GRUB_TIMEOUT=10" in content
    assert "GRUB_DISABLE_OS_PROBER=true" in content
    assert 'GRUB_DEFAULT="1>6"' in content       # preserva resto


def test_backs_up_before_apply(tmp_path):
    apply, _, _ = _make(tmp_path)
    apply.execute({"GRUB_TIMEOUT": "3"})
    backups = list((tmp_path / "backups").glob("grub.*"))
    assert backups and "GRUB_TIMEOUT=5" in backups[0].read_text()


def test_does_not_write_file_directly(tmp_path):
    apply, _, grub = _make(tmp_path)
    apply.execute({"GRUB_TIMEOUT": "3"})
    assert grub.read_text() == GRUB
