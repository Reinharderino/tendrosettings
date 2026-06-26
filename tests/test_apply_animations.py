from unittest.mock import MagicMock

from ajustes.core.animations import AnimationsSettings
from ajustes.core.apply_animations import ApplyAnimations
from ajustes.core.config_store import ConfigStore


def _make_apply(tmp_path, available=True):
    store = ConfigStore(settings_dir=tmp_path / "settings")
    bridge = MagicMock()
    bridge.is_available.return_value = available
    return ApplyAnimations(store=store, bridge=bridge), bridge


def test_apply_writes_json(tmp_path):
    apply, _ = _make_apply(tmp_path)
    apply.execute(AnimationsSettings.defaults())
    result = ConfigStore(settings_dir=tmp_path / "settings").read("animations")
    assert result is not None
    assert any(leaf["name"] == "windows" for leaf in result["animations"])


def test_apply_reloads_when_available(tmp_path):
    apply, bridge = _make_apply(tmp_path, available=True)
    apply.execute(AnimationsSettings.defaults())
    bridge.reload.assert_called_once()


def test_apply_does_not_reload_when_unavailable(tmp_path):
    apply, bridge = _make_apply(tmp_path, available=False)
    apply.execute(AnimationsSettings.defaults())
    bridge.reload.assert_not_called()


def test_apply_returns_applied_live(tmp_path):
    apply, _ = _make_apply(tmp_path, available=True)
    assert apply.execute(AnimationsSettings.defaults()).applied_live is True
