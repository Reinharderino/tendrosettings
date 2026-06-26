import pytest

from ajustes.core.animations import (
    BEZIER_CHOICES,
    CONFIGURABLE_LEAVES,
    AnimationLeaf,
    AnimationsSettings,
)


def test_leaf_round_trip():
    leaf = AnimationLeaf(name="windows", enabled=True, speed=7.0, bezier="myBezier", style="popin 80%")
    assert AnimationLeaf.from_dict(leaf.to_dict()) == leaf


def test_leaf_from_dict_clamps_speed():
    assert AnimationLeaf.from_dict({"name": "fade", "speed": 0.0}).speed == 0.1
    assert AnimationLeaf.from_dict({"name": "fade", "speed": 999}).speed == 50.0


def test_leaf_from_dict_unknown_bezier_falls_back_to_default():
    leaf = AnimationLeaf.from_dict({"name": "border", "bezier": "nonexistent"})
    assert leaf.bezier == "default"


def test_leaf_from_dict_known_bezier_preserved():
    leaf = AnimationLeaf.from_dict({"name": "border", "bezier": "myBezier"})
    assert leaf.bezier == "myBezier"


def test_leaf_from_dict_style_stripped():
    assert AnimationLeaf.from_dict({"name": "fade", "style": "  slide  "}).style == "slide"


def test_defaults_cover_all_configurable_leaves():
    settings = AnimationsSettings.defaults()
    names = {leaf.name for leaf in settings.leaves}
    assert names == set(CONFIGURABLE_LEAVES)


def test_defaults_match_current_hyprland_lua():
    by_name = {leaf.name: leaf for leaf in AnimationsSettings.defaults().leaves}
    assert (by_name["windows"].speed, by_name["windows"].bezier) == (7.0, "myBezier")
    assert (by_name["border"].speed, by_name["border"].bezier) == (10.0, "default")
    assert (by_name["borderangle"].speed) == 8.0
    assert (by_name["workspaces"].speed) == 6.0
    assert by_name["windowsOut"].style == "popin 80%"


def test_settings_round_trip():
    settings = AnimationsSettings.defaults()
    assert AnimationsSettings.from_dict(settings.to_dict()) == settings


def test_settings_from_dict_empty_uses_defaults():
    assert AnimationsSettings.from_dict({}) == AnimationsSettings.defaults()


def test_settings_from_dict_unknown_leaf_ignored():
    settings = AnimationsSettings.from_dict({
        "animations": [{"name": "not_a_real_leaf", "enabled": True, "speed": 5}]
    })
    names = {leaf.name for leaf in settings.leaves}
    assert "not_a_real_leaf" not in names


def test_settings_from_dict_missing_leaf_filled_from_defaults():
    # Solo provee 'fade'; el resto debe completarse con defaults.
    settings = AnimationsSettings.from_dict({
        "animations": [{"name": "fade", "enabled": False, "speed": 3, "bezier": "linear"}]
    })
    by_name = {leaf.name: leaf for leaf in settings.leaves}
    assert set(by_name) == set(CONFIGURABLE_LEAVES)
    assert by_name["fade"].enabled is False
    assert by_name["fade"].speed == 3.0
    assert by_name["border"] == next(
        leaf for leaf in AnimationsSettings.defaults().leaves if leaf.name == "border"
    )


def test_bezier_choices_includes_defaults():
    assert "default" in BEZIER_CHOICES
    assert "linear" in BEZIER_CHOICES
    assert "myBezier" in BEZIER_CHOICES
