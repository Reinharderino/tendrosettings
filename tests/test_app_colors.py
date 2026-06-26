import configparser

import pytest

from ajustes.core.app_colors import (
    GNOME_ACCENTS,
    AppColorsSettings,
    generate_color_scheme,
    hex_to_rgb_csv,
    is_dark,
    nearest_gnome_accent,
    normalize_hex,
)


# --- hex helpers ---

def test_normalize_hex_uppercase_and_hash():
    assert normalize_hex("#E8D5B0") == "#e8d5b0"
    assert normalize_hex("e8d5b0") == "#e8d5b0"


def test_normalize_hex_invalid_returns_none():
    assert normalize_hex("nope") is None
    assert normalize_hex("#12") is None


def test_hex_to_rgb_csv():
    assert hex_to_rgb_csv("#0c0a08") == "12,10,8"
    assert hex_to_rgb_csv("#ffffff") == "255,255,255"


# --- luminance / dark ---

def test_is_dark_true_for_dark_bg():
    assert is_dark("#0c0a08") is True


def test_is_dark_false_for_light_bg():
    assert is_dark("#f5f5f5") is False


# --- nearest gnome accent ---

def test_nearest_gnome_accent_orange_family():
    # #cd853f (peru/dorado) cae en la familia naranja/amarilla de GNOME
    assert nearest_gnome_accent("#cd853f") in {"orange", "yellow"}


def test_nearest_gnome_accent_pure_blue():
    assert nearest_gnome_accent("#3584e4") == "blue"


def test_nearest_gnome_accent_always_valid_name():
    assert nearest_gnome_accent("#000000") in GNOME_ACCENTS
    assert nearest_gnome_accent("#ffffff") in GNOME_ACCENTS


# --- settings ---

def make_settings(**kw):
    defaults = dict(text_color="#e8d5b0", background_color="#0c0a08",
                    accent_color="#cd853f", sync_gtk=True)
    return AppColorsSettings(**{**defaults, **kw})


def test_settings_round_trip():
    s = make_settings(text_color="#ffffff", sync_gtk=False)
    assert AppColorsSettings.from_dict(s.to_dict()) == s


def test_settings_from_dict_invalid_color_falls_back_to_default():
    s = AppColorsSettings.from_dict({"text_color": "garbage"})
    assert s.text_color == AppColorsSettings.defaults().text_color


def test_settings_from_dict_normalizes_color():
    s = AppColorsSettings.from_dict({"accent_color": "#CD853F"})
    assert s.accent_color == "#cd853f"


def test_settings_from_dict_empty_uses_defaults():
    assert AppColorsSettings.from_dict({}) == AppColorsSettings.defaults()


# --- generación del esquema .colors ---

REQUIRED_GROUPS = [
    "Colors:View", "Colors:Window", "Colors:Button",
    "Colors:Selection", "Colors:Tooltip", "Colors:Complementary",
]


def _parse_scheme(content: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # preservar mayúsculas en claves KDE
    parser.read_string(content)
    return parser


def test_scheme_has_required_groups_and_name():
    content = generate_color_scheme("#e8d5b0", "#0c0a08", "#cd853f", "MiTema")
    parser = _parse_scheme(content)
    for group in REQUIRED_GROUPS:
        assert parser.has_section(group), f"falta {group}"
    assert parser.get("General", "Name") == "MiTema"


def test_scheme_text_and_bg_applied_to_view_and_window():
    content = generate_color_scheme("#e8d5b0", "#0c0a08", "#cd853f", "T")
    parser = _parse_scheme(content)
    for group in ("Colors:View", "Colors:Window"):
        assert parser.get(group, "ForegroundNormal") == "232,213,176"
        assert parser.get(group, "BackgroundNormal") == "12,10,8"


def test_scheme_accent_applied_to_selection_and_decoration():
    content = generate_color_scheme("#e8d5b0", "#0c0a08", "#cd853f", "T")
    parser = _parse_scheme(content)
    assert parser.get("Colors:Selection", "BackgroundNormal") == "205,133,63"
    assert parser.get("Colors:View", "DecorationFocus") == "205,133,63"
