from unittest.mock import MagicMock

from ajustes.core.appearance import AppearanceSettings
from ajustes.core.apply_appearance import ApplyAppearance
from ajustes.core.config_store import ConfigStore


def _make_apply(tmp_path, available=True):
    store = ConfigStore(settings_dir=tmp_path / "settings")
    bridge = MagicMock()
    bridge.is_available.return_value = available
    return ApplyAppearance(store=store, bridge=bridge), bridge


def test_apply_writes_json(tmp_path):
    apply, _ = _make_apply(tmp_path)
    settings = AppearanceSettings.defaults()
    apply.execute(settings)
    result = ConfigStore(settings_dir=tmp_path / "settings").read("appearance")
    assert result is not None
    assert result["gaps_in"] == 5
    assert result["active_color_1"] == "rgba(33ccffee)"


def test_apply_reloads_when_available(tmp_path):
    apply, bridge = _make_apply(tmp_path, available=True)
    apply.execute(AppearanceSettings.defaults())
    bridge.reload.assert_called_once()


def test_apply_does_not_reload_when_unavailable(tmp_path):
    apply, bridge = _make_apply(tmp_path, available=False)
    apply.execute(AppearanceSettings.defaults())
    bridge.reload.assert_not_called()


def test_apply_returns_applied_live(tmp_path):
    apply, _ = _make_apply(tmp_path, available=True)
    assert apply.execute(AppearanceSettings.defaults()).applied_live is True

    apply2, _ = _make_apply(tmp_path, available=False)
    assert apply2.execute(AppearanceSettings.defaults()).applied_live is False
