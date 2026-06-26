import dataclasses

from unittest.mock import MagicMock

from ajustes.core.app_colors import AppColorsSettings
from ajustes.core.apply_app_colors import SCHEME_NAME, ApplyAppColors
from ajustes.core.config_store import ConfigStore


def _make_apply(tmp_path, kdeglobals=None):
    store = ConfigStore(settings_dir=tmp_path / "settings")
    bridge = MagicMock()
    schemes_dir = tmp_path / "color-schemes"
    kde_path = kdeglobals if kdeglobals is not None else tmp_path / "kdeglobals"
    apply = ApplyAppColors(store=store, bridge=bridge, schemes_dir=schemes_dir,
                           kdeglobals_path=kde_path)
    return apply, bridge, schemes_dir, store


def test_persists_json(tmp_path):
    apply, *_ = _make_apply(tmp_path)
    apply.execute(AppColorsSettings.defaults())
    result = ConfigStore(settings_dir=tmp_path / "settings").read("app_colors")
    assert result is not None
    assert result["text_color"] == "#e8d5b0"


def test_writes_scheme_file(tmp_path):
    apply, _, schemes_dir, _ = _make_apply(tmp_path)
    apply.execute(AppColorsSettings.defaults())
    scheme_file = schemes_dir / f"{SCHEME_NAME}.colors"
    assert scheme_file.exists()
    content = scheme_file.read_text()
    assert f"Name={SCHEME_NAME}" in content
    assert "232,213,176" in content  # texto por defecto en R,G,B


def test_applies_kde_scheme(tmp_path):
    apply, bridge, _, _ = _make_apply(tmp_path)
    apply.execute(AppColorsSettings.defaults())
    bridge.apply_kde_scheme.assert_called_once_with(SCHEME_NAME)


def test_backs_up_existing_kdeglobals_before_apply(tmp_path):
    kde = tmp_path / "kdeglobals"
    kde.write_text("[General]\nfont=Old\n", encoding="utf-8")
    apply, _, _, store = _make_apply(tmp_path, kdeglobals=kde)
    apply.execute(AppColorsSettings.defaults())
    backups = list(store.backups_dir().glob("kdeglobals.*"))
    assert backups, "debió respaldar kdeglobals antes de aplicar"
    assert "font=Old" in backups[0].read_text()


def test_no_backup_when_kdeglobals_absent(tmp_path):
    apply, _, _, store = _make_apply(tmp_path)  # kdeglobals no existe
    apply.execute(AppColorsSettings.defaults())  # no debe fallar
    assert not list(store.backups_dir().glob("kdeglobals.*"))


def test_sync_gtk_true_applies_gtk_with_dark_and_accent(tmp_path):
    apply, bridge, _, _ = _make_apply(tmp_path)
    apply.execute(AppColorsSettings.defaults())  # fondo oscuro -> prefer_dark True
    bridge.apply_gtk.assert_called_once()
    kwargs = bridge.apply_gtk.call_args.kwargs
    assert kwargs["prefer_dark"] is True
    assert kwargs["accent_name"] in {"orange", "yellow"}


def test_sync_gtk_false_skips_gtk(tmp_path):
    apply, bridge, _, _ = _make_apply(tmp_path)
    apply.execute(dataclasses.replace(AppColorsSettings.defaults(), sync_gtk=False))
    bridge.apply_gtk.assert_not_called()


def test_light_background_derives_prefer_light(tmp_path):
    apply, bridge, _, _ = _make_apply(tmp_path)
    apply.execute(dataclasses.replace(
        AppColorsSettings.defaults(), background_color="#f5f5f5", text_color="#202020"))
    assert bridge.apply_gtk.call_args.kwargs["prefer_dark"] is False
