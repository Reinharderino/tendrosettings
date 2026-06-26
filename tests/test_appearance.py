import pytest

from ajustes.core.appearance import (
    AppearanceSettings,
    hypr_color_to_rgba_floats,
    rgba_floats_to_hypr_color,
)


def make_settings(**kwargs) -> AppearanceSettings:
    defaults = dict(
        gaps_in=5, gaps_out=10, border_size=2,
        rounding=10, blur_enabled=True, blur_size=3, blur_passes=1,
        animations_enabled=True,
        active_color_1="rgba(33ccffee)", active_color_2="rgba(00ff99ee)",
        gradient_angle=45, inactive_color="rgba(595959aa)",
    )
    return AppearanceSettings(**{**defaults, **kwargs})


def test_round_trip():
    settings = make_settings(gaps_in=8, rounding=20, blur_enabled=False)
    assert AppearanceSettings.from_dict(settings.to_dict()) == settings


def test_from_dict_missing_fields_use_defaults():
    settings = AppearanceSettings.from_dict({})
    assert settings == AppearanceSettings.defaults()


def test_defaults_match_current_look_and_feel():
    d = AppearanceSettings.defaults()
    assert (d.gaps_in, d.gaps_out, d.border_size) == (5, 10, 2)
    assert (d.rounding, d.blur_enabled, d.blur_size, d.blur_passes) == (10, True, 3, 1)
    assert d.animations_enabled is True
    assert d.active_color_1 == "rgba(33ccffee)"
    assert d.gradient_angle == 45


@pytest.mark.parametrize("field,value,expected", [
    ("gaps_in", -5, 0), ("gaps_in", 500, 100),
    ("gaps_out", -1, 0), ("gaps_out", 999, 100),
    ("border_size", -3, 0), ("border_size", 99, 20),
    ("rounding", -2, 0), ("rounding", 200, 50),
    ("blur_size", 0, 1), ("blur_size", 50, 20),
    ("blur_passes", 0, 1), ("blur_passes", 99, 10),
    ("gradient_angle", -10, 0), ("gradient_angle", 400, 360),
])
def test_from_dict_clamps_numeric_fields(field, value, expected):
    settings = AppearanceSettings.from_dict({field: value})
    assert getattr(settings, field) == expected


def test_from_dict_invalid_color_falls_back_to_default():
    settings = AppearanceSettings.from_dict({"active_color_1": "not-a-color"})
    assert settings.active_color_1 == AppearanceSettings.defaults().active_color_1


def test_from_dict_accepts_rgb_and_rgba_colors():
    settings = AppearanceSettings.from_dict({
        "active_color_1": "rgb(112233)",
        "inactive_color": "rgba(aabbccdd)",
    })
    assert settings.active_color_1 == "rgb(112233)"
    assert settings.inactive_color == "rgba(aabbccdd)"


def test_from_dict_color_normalized_lowercase():
    settings = AppearanceSettings.from_dict({"active_color_1": "RGBA(33CCFFEE)"})
    assert settings.active_color_1 == "rgba(33ccffee)"


# --- conversión de color hyprland <-> floats RGBA (0-1) para el color picker ---

def test_hypr_color_to_rgba_floats_rgba():
    r, g, b, a = hypr_color_to_rgba_floats("rgba(ff0000ff)")
    assert (round(r), round(g), round(b), round(a)) == (1, 0, 0, 1)


def test_hypr_color_to_rgba_floats_rgb_defaults_alpha_one():
    _, _, _, a = hypr_color_to_rgba_floats("rgb(00ff00)")
    assert a == 1.0


def test_hypr_color_to_rgba_floats_half_alpha():
    *_, a = hypr_color_to_rgba_floats("rgba(00000080)")
    assert abs(a - 128 / 255) < 1e-6


def test_hypr_color_to_rgba_floats_invalid_falls_back_to_opaque_black():
    assert hypr_color_to_rgba_floats("garbage") == (0.0, 0.0, 0.0, 1.0)


def test_rgba_floats_to_hypr_color_round_trip():
    original = "rgba(33ccffee)"
    assert rgba_floats_to_hypr_color(*hypr_color_to_rgba_floats(original)) == original


def test_rgba_floats_to_hypr_color_clamps_out_of_range():
    assert rgba_floats_to_hypr_color(2.0, -1.0, 0.0, 0.5) == "rgba(ff000080)"
