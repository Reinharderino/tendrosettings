import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from ajustes.core.apply_monitors import ApplyMonitors
from ajustes.core.config_store import ConfigStore
from ajustes.core.errors import HyprlandUnavailableError
from ajustes.core.hyprland_bridge import HyprctlBridge
from ajustes.core.monitors import (
    MonitorSpec,
    MonitorSettings,
    PowerSettings,
    generate_hypridle_conf,
    mode_string,
    parse_modes,
)


def make_spec(**kwargs):
    defaults = dict(name="DP-1", mode="3440x1440@144.00Hz", scale=1.0,
                    x=0, y=0, transform=0, enabled=True)
    return MonitorSpec(**{**defaults, **kwargs})


def make_settings(monitors=None, power=None):
    monitors = [make_spec()] if monitors is None else monitors
    power = power or PowerSettings()
    return MonitorSettings(monitors=tuple(monitors), power=power)


def test_monitor_spec_round_trip():
    spec = make_spec(name="DP-2", mode="1920x1080@144.00Hz", scale=1.5,
                     x=3440, y=0, transform=1, enabled=False)
    assert MonitorSpec.from_dict(spec.to_dict()) == spec


def test_monitor_spec_from_dict_transform_out_of_range_normalizes_to_zero():
    spec = MonitorSpec.from_dict({"name": "DP-1", "mode": "preferred",
                                  "scale": 1.0, "x": 0, "y": 0,
                                  "transform": 99, "enabled": True})
    assert spec.transform == 0


def test_monitor_spec_from_dict_scale_clamped_low():
    spec = MonitorSpec.from_dict({"name": "DP-1", "mode": "preferred",
                                  "scale": 0.1, "x": 0, "y": 0,
                                  "transform": 0, "enabled": True})
    assert spec.scale == 0.5


def test_monitor_spec_from_dict_scale_clamped_high():
    spec = MonitorSpec.from_dict({"name": "DP-1", "mode": "preferred",
                                  "scale": 5.0, "x": 0, "y": 0,
                                  "transform": 0, "enabled": True})
    assert spec.scale == 3.0


def test_monitor_spec_from_dict_missing_fields_use_defaults():
    spec = MonitorSpec.from_dict({"name": "DP-1"})
    assert spec.mode == "preferred"
    assert spec.scale == 1.0
    assert spec.x == 0
    assert spec.y == 0
    assert spec.transform == 0
    assert spec.enabled is True


def test_power_settings_round_trip():
    ps = PowerSettings(suspend_minutes=5, off_minutes=15)
    assert PowerSettings.from_dict(ps.to_dict()) == ps


def test_power_off_less_than_or_equal_suspend_raises():
    with pytest.raises(ValueError, match="off_minutes"):
        PowerSettings.from_dict({"suspend_minutes": 10, "off_minutes": 5})


def test_power_off_equal_suspend_raises():
    with pytest.raises(ValueError, match="off_minutes"):
        PowerSettings.from_dict({"suspend_minutes": 10, "off_minutes": 10})


def test_power_suspend_zero_off_nonzero_is_valid():
    ps = PowerSettings.from_dict({"suspend_minutes": 0, "off_minutes": 5})
    assert ps.suspend_minutes == 0
    assert ps.off_minutes == 5


def test_power_both_zero_is_valid():
    ps = PowerSettings.from_dict({"suspend_minutes": 0, "off_minutes": 0})
    assert ps.suspend_minutes == 0


def test_power_direct_construction_validates():
    with pytest.raises(ValueError, match="off_minutes"):
        PowerSettings(suspend_minutes=10, off_minutes=5)


def test_monitor_settings_round_trip():
    settings = make_settings(
        monitors=[make_spec(), make_spec(name="DP-2", x=3440)],
        power=PowerSettings(suspend_minutes=3, off_minutes=10),
    )
    assert MonitorSettings.from_dict(settings.to_dict()) == settings


def test_monitor_settings_from_dict_empty_monitors():
    settings = MonitorSettings.from_dict({})
    assert settings.monitors == ()


# --- parse_modes ---

def test_parse_modes_agrupa_por_resolucion():
    modes = ["3440x1440@144.00Hz", "3440x1440@60.00Hz", "1920x1080@60.00Hz"]
    result = parse_modes(modes)
    assert set(result.keys()) == {"3440x1440", "1920x1080"}
    assert result["3440x1440"] == [144.0, 60.0]  # ordenadas descendente


def test_parse_modes_ignora_strings_invalidos():
    result = parse_modes(["invalid", "3440x1440@144.00Hz"])
    assert "3440x1440" in result
    assert len(result) == 1


def test_parse_modes_lista_vacia():
    assert parse_modes([]) == {}


def test_mode_string_formato():
    assert mode_string("3440x1440", 144.0) == "3440x1440@144.00Hz"
    assert mode_string("1920x1080", 59.94) == "1920x1080@59.94Hz"


# --- generate_hypridle_conf ---

def test_generate_hypridle_conf_ambos_activos():
    power = PowerSettings(suspend_minutes=5, off_minutes=15)
    conf = generate_hypridle_conf(power)
    assert "timeout = 300" in conf        # 5 * 60
    assert "dpms off" in conf
    assert "timeout = 900" in conf        # 15 * 60
    assert "systemctl suspend" in conf


def test_generate_hypridle_conf_solo_suspend():
    power = PowerSettings(suspend_minutes=5, off_minutes=0)
    conf = generate_hypridle_conf(power)
    assert "timeout = 300" in conf
    assert "systemctl suspend" not in conf


def test_generate_hypridle_conf_ambos_cero_vacio():
    power = PowerSettings(suspend_minutes=0, off_minutes=0)
    conf = generate_hypridle_conf(power)
    assert "listener" not in conf


SAMPLE_MONITORS_JSON = json.dumps([
    {
        "name": "DP-1",
        "width": 3440, "height": 1440, "refreshRate": 50.0,
        "x": 0, "y": 0, "scale": 1.0, "transform": 0,
        "availableModes": ["3440x1440@144.00Hz", "3440x1440@60.00Hz"],
    }
])


def _bridge_with_monitors(stdout=SAMPLE_MONITORS_JSON, returncode=0):
    run = MagicMock(return_value=MagicMock(stdout=stdout, returncode=returncode))
    return HyprctlBridge(run=run), run


def test_monitors_info_devuelve_lista():
    bridge, _ = _bridge_with_monitors()
    result = bridge.monitors_info()
    assert isinstance(result, list)
    assert result[0]["name"] == "DP-1"
    assert "availableModes" in result[0]


def test_monitors_info_json_invalido_lanza():
    bridge, _ = _bridge_with_monitors(stdout="no json")
    with pytest.raises(HyprlandUnavailableError):
        bridge.monitors_info()


def test_monitors_info_codigo_error_lanza():
    bridge, _ = _bridge_with_monitors(returncode=1)
    with pytest.raises(HyprlandUnavailableError):
        bridge.monitors_info()


def test_restart_hypridle_ok():
    run = MagicMock(return_value=MagicMock(returncode=0))
    bridge = HyprctlBridge(run=run)
    bridge.restart_hypridle()  # must not raise
    run.assert_called_once_with(["systemctl", "--user", "restart", "hypridle"])


def test_restart_hypridle_no_instalado_no_lanza():
    run = MagicMock(return_value=MagicMock(returncode=5))  # unit not found
    bridge = HyprctlBridge(run=run)
    bridge.restart_hypridle()  # must silently swallow the error


# --- ApplyMonitors ---


def _make_apply(tmp_path, available=True):
    store = ConfigStore(settings_dir=tmp_path / "settings")
    bridge = MagicMock()
    bridge.is_available.return_value = available
    hypridle_conf = tmp_path / "hypridle.conf"
    return ApplyMonitors(store=store, bridge=bridge, hypridle_conf_path=hypridle_conf), bridge, hypridle_conf


def _make_monitor_settings():
    return MonitorSettings(
        monitors=(make_spec(name="DP-1", mode="3440x1440@144.00Hz"),),
        power=PowerSettings(suspend_minutes=5, off_minutes=15),
    )


def test_apply_monitors_escribe_json(tmp_path):
    apply, bridge, _ = _make_apply(tmp_path)
    settings = _make_monitor_settings()
    apply.execute(settings)
    result = ConfigStore(settings_dir=tmp_path / "settings").read("monitors")
    assert result is not None
    assert result["monitors"][0]["name"] == "DP-1"


def test_apply_monitors_escribe_hypridle_conf(tmp_path):
    apply, bridge, hypridle_conf = _make_apply(tmp_path)
    apply.execute(_make_monitor_settings())
    assert hypridle_conf.exists()
    content = hypridle_conf.read_text()
    assert "timeout = 300" in content    # 5 min
    assert "timeout = 900" in content    # 15 min


def test_apply_monitors_recarga_hyprland_si_disponible(tmp_path):
    apply, bridge, _ = _make_apply(tmp_path, available=True)
    apply.execute(_make_monitor_settings())
    bridge.reload.assert_called_once()
    bridge.restart_hypridle.assert_called_once()


def test_apply_monitors_no_recarga_si_no_disponible(tmp_path):
    apply, bridge, _ = _make_apply(tmp_path, available=False)
    apply.execute(_make_monitor_settings())
    bridge.reload.assert_not_called()
    bridge.restart_hypridle.assert_not_called()


def test_apply_monitors_devuelve_applied_live(tmp_path):
    apply, bridge, _ = _make_apply(tmp_path, available=True)
    result = apply.execute(_make_monitor_settings())
    assert result.applied_live is True

    apply2, _, _ = _make_apply(tmp_path, available=False)
    result2 = apply2.execute(_make_monitor_settings())
    assert result2.applied_live is False
