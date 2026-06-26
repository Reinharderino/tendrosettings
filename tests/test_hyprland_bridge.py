import json
from dataclasses import dataclass, field

import pytest

from ajustes.core.errors import HyprlandUnavailableError
from ajustes.core.hyprland_bridge import ANIMATED_WALLPAPER_SCRIPT, HyprctlBridge


@dataclass
class FakeRunner:
    stdout: str = ""
    returncode: int = 0
    stderr: str = ""
    commands: list = field(default_factory=list)

    def __call__(self, args):
        self.commands.append(args)

        @dataclass
        class Result:
            stdout: str
            returncode: int
            stderr: str

        return Result(stdout=self.stdout, returncode=self.returncode, stderr=self.stderr)


def test_is_available_depende_de_la_signature_de_hyprland():
    runner = FakeRunner()

    assert HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"}).is_available()
    assert not HyprctlBridge(run=runner, env={}).is_available()


def test_monitor_names_parsea_hyprctl_monitors():
    runner = FakeRunner(stdout=json.dumps([{"name": "DP-1"}, {"name": "DP-2"}]))
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    assert bridge.monitor_names() == ["DP-1", "DP-2"]
    assert runner.commands == [["hyprctl", "monitors", "-j"]]


def test_set_wallpaper_construye_el_comando_ipc():
    runner = FakeRunner(stdout="ok")
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    bridge.set_wallpaper("DP-1", "/fondos/a.jpg")

    assert runner.commands == [
        ["hyprctl", "hyprpaper", "wallpaper", "DP-1,/fondos/a.jpg"]
    ]


def test_set_animated_wallpaper_invoca_el_script_con_parametros():
    runner = FakeRunner(stdout="ok")
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    bridge.set_animated_wallpaper("DP-2", "/v/Maiden.gif", "cover")

    assert runner.commands == [
        [ANIMATED_WALLPAPER_SCRIPT, "--output", "DP-2", "--fit", "cover", "/v/Maiden.gif"]
    ]


def test_set_animated_wallpaper_lanza_dominio_si_el_script_falla():
    runner = FakeRunner(stdout="swww no está instalado", returncode=2)
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    with pytest.raises(HyprlandUnavailableError):
        bridge.set_animated_wallpaper("DP-2", "/v/Maiden.gif", "cover")


def test_set_animated_wallpaper_lanza_dominio_si_no_hay_script():
    def missing_binary(args):
        raise FileNotFoundError("wallpaper-swww.sh")

    bridge = HyprctlBridge(run=missing_binary, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    with pytest.raises(HyprlandUnavailableError):
        bridge.set_animated_wallpaper("DP-2", "/v/Maiden.gif", "cover")


def test_verify_config_devuelve_none_si_ok():
    runner = FakeRunner(stdout="config ok", returncode=0)
    bridge = HyprctlBridge(run=runner, env={})

    assert bridge.verify_config() is None


def test_verify_config_devuelve_salida_si_falla():
    runner = FakeRunner(stdout="error en línea 3", returncode=1)
    bridge = HyprctlBridge(run=runner, env={})

    assert "línea 3" in bridge.verify_config()


def test_monitor_names_lanza_dominio_si_hyprctl_falla():
    runner = FakeRunner(stdout="Couldn't connect to socket", returncode=1)
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    with pytest.raises(HyprlandUnavailableError):
        bridge.monitor_names()


def test_monitor_names_lanza_dominio_si_no_hay_binario():
    def missing_binary(args):
        raise FileNotFoundError("hyprctl")

    bridge = HyprctlBridge(run=missing_binary, env={})

    with pytest.raises(HyprlandUnavailableError):
        bridge.monitor_names()


def test_set_wallpaper_lanza_dominio_si_ipc_falla():
    runner = FakeRunner(stdout="wallpaper failed (not preloaded)", returncode=1)
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    with pytest.raises(HyprlandUnavailableError):
        bridge.set_wallpaper("DP-1", "/fondos/a.jpg")


def test_verify_config_limpia_codigos_ansi():
    runner = FakeRunner(stdout="\x1b[1;32merror\x1b[0m en línea 3", returncode=1)
    bridge = HyprctlBridge(run=runner, env={})

    assert bridge.verify_config() == "error en línea 3"


def test_get_binds_devuelve_la_lista_cruda():
    raw = [{"modmask": 64, "key": "B", "dispatcher": "__lua", "arg": "7",
            "mouse": False, "submap": "", "description": ""}]
    runner = FakeRunner(stdout=json.dumps(raw))
    bridge = HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})

    assert bridge.get_binds() == raw
    assert runner.commands == [["hyprctl", "binds", "-j"]]


def test_get_binds_lanza_dominio_si_falla_o_no_es_lista():
    bridge_err = HyprctlBridge(run=FakeRunner(stdout="error", returncode=1),
                               env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})
    with pytest.raises(HyprlandUnavailableError):
        bridge_err.get_binds()

    bridge_obj = HyprctlBridge(run=FakeRunner(stdout='{"no": "lista"}'),
                               env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})
    with pytest.raises(HyprlandUnavailableError):
        bridge_obj.get_binds()

    bridge_json = HyprctlBridge(run=FakeRunner(stdout="{rotísimo"),
                                env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})
    with pytest.raises(HyprlandUnavailableError):
        bridge_json.get_binds()


def test_reload_invoca_hyprctl_y_traduce_fallos():
    runner = FakeRunner(stdout="ok")
    HyprctlBridge(run=runner, env={"HYPRLAND_INSTANCE_SIGNATURE": "x"}).reload()
    assert runner.commands == [["hyprctl", "reload"]]

    failing = HyprctlBridge(run=FakeRunner(stdout="err", returncode=1),
                            env={"HYPRLAND_INSTANCE_SIGNATURE": "x"})
    with pytest.raises(HyprlandUnavailableError):
        failing.reload()
