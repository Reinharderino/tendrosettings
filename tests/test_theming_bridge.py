from unittest.mock import MagicMock

import pytest

from ajustes.core.errors import ThemingError
from ajustes.core.theming_bridge import KdeGtkBridge


def _ok_run(calls):
    def run(args):
        calls.append(args)
        return MagicMock(returncode=0, stdout="")
    return run


def test_apply_kde_scheme_invoca_plasma_apply():
    calls = []
    KdeGtkBridge(run=_ok_run(calls)).apply_kde_scheme("MiTema")
    assert ["plasma-apply-colorscheme", "MiTema"] in calls


def test_apply_kde_scheme_codigo_error_lanza():
    run = MagicMock(return_value=MagicMock(returncode=1, stdout="boom"))
    with pytest.raises(ThemingError):
        KdeGtkBridge(run=run).apply_kde_scheme("X")


def test_apply_kde_scheme_binario_ausente_lanza():
    def run(_args):
        raise FileNotFoundError
    with pytest.raises(ThemingError):
        KdeGtkBridge(run=run).apply_kde_scheme("X")


def test_apply_gtk_dark_setea_prefer_dark():
    calls = []
    KdeGtkBridge(run=_ok_run(calls)).apply_gtk(prefer_dark=True, accent_name=None)
    assert ["gsettings", "set", "org.gnome.desktop.interface",
            "color-scheme", "prefer-dark"] in calls


def test_apply_gtk_light_setea_prefer_light():
    calls = []
    KdeGtkBridge(run=_ok_run(calls)).apply_gtk(prefer_dark=False, accent_name=None)
    assert ["gsettings", "set", "org.gnome.desktop.interface",
            "color-scheme", "prefer-light"] in calls


def test_apply_gtk_con_accent_setea_accent_color():
    calls = []
    KdeGtkBridge(run=_ok_run(calls)).apply_gtk(prefer_dark=True, accent_name="orange")
    assert ["gsettings", "set", "org.gnome.desktop.interface",
            "accent-color", "orange"] in calls


def test_apply_gtk_sin_accent_no_setea_accent_color():
    calls = []
    KdeGtkBridge(run=_ok_run(calls)).apply_gtk(prefer_dark=True, accent_name=None)
    assert not any("accent-color" in c for c in calls)
