from dataclasses import dataclass, field

import pytest

from ajustes.core.apply_wallpaper import ApplyWallpaper
from ajustes.core.config_store import ConfigStore
from ajustes.core.errors import HyprlandUnavailableError, InvalidWallpaperError
from ajustes.core.wallpaper import WallpaperSettings


@dataclass
class FakeBridge:
    available: bool = True
    applied: list = field(default_factory=list)
    animated_applied: list = field(default_factory=list)

    def is_available(self):
        return self.available

    def monitor_names(self):
        return ["DP-1", "DP-2"]

    def set_wallpaper(self, monitor, image_path):
        self.applied.append((monitor, image_path))

    def set_animated_wallpaper(self, monitor, image_path, fit_mode="cover"):
        self.animated_applied.append((monitor, image_path, fit_mode))

    def verify_config(self):
        return None


@pytest.fixture
def image(tmp_path):
    path = tmp_path / "fondo.jpg"
    path.write_bytes(b"\xff\xd8fake")
    return path


@pytest.fixture
def gif(tmp_path):
    path = tmp_path / "loop.gif"
    path.write_bytes(b"GIF89a")
    return path


def make_use_case(tmp_path, bridge):
    return ApplyWallpaper(
        store=ConfigStore(settings_dir=tmp_path / "settings"),
        bridge=bridge,
        hyprpaper_conf_path=tmp_path / "hyprpaper.conf",
    )


def test_aplica_persiste_y_lanza_ipc(tmp_path, image):
    bridge = FakeBridge()
    use_case = make_use_case(tmp_path, bridge)

    result = use_case.execute(WallpaperSettings(), monitor="DP-1", image_path=image)

    assert result.applied_live is True
    assert bridge.applied == [("DP-1", str(image))]
    assert result.settings.monitors["DP-1"].path == str(image)
    saved = (tmp_path / "settings" / "wallpaper.json").read_text(encoding="utf-8")
    assert "fondo.jpg" in saved
    conf = (tmp_path / "hyprpaper.conf").read_text(encoding="utf-8")
    assert f"path = {image}" in conf


def test_animado_va_por_swww_y_se_marca_animated(tmp_path, gif):
    bridge = FakeBridge()
    use_case = make_use_case(tmp_path, bridge)

    result = use_case.execute(WallpaperSettings(), monitor="DP-2", image_path=gif)

    assert result.applied_live is True
    # va por swww (con fit por defecto), NO por el IPC de hyprpaper
    assert bridge.animated_applied == [("DP-2", str(gif), "cover")]
    assert bridge.applied == []
    assert result.settings.monitors["DP-2"].animated is True
    # el gif NO debe escribirse en hyprpaper.conf (lo maneja swww)
    conf = (tmp_path / "hyprpaper.conf").read_text(encoding="utf-8")
    assert "loop.gif" not in conf
    saved = (tmp_path / "settings" / "wallpaper.json").read_text(encoding="utf-8")
    assert '"animated": true' in saved


def test_animado_persiste_pero_no_aplica_sin_sesion(tmp_path, gif):
    bridge = FakeBridge(available=False)
    use_case = make_use_case(tmp_path, bridge)

    result = use_case.execute(WallpaperSettings(), monitor="DP-2", image_path=gif)

    assert result.applied_live is False
    assert bridge.animated_applied == []
    saved = (tmp_path / "settings" / "wallpaper.json").read_text(encoding="utf-8")
    assert '"animated": true' in saved


def test_sin_sesion_persiste_pero_no_aplica(tmp_path, image):
    bridge = FakeBridge(available=False)
    use_case = make_use_case(tmp_path, bridge)

    result = use_case.execute(WallpaperSettings(), monitor="DP-1", image_path=image)

    assert result.applied_live is False
    assert bridge.applied == []
    assert (tmp_path / "settings" / "wallpaper.json").exists()


def test_imagen_inexistente_rechazada_sin_escribir(tmp_path):
    bridge = FakeBridge()
    use_case = make_use_case(tmp_path, bridge)

    with pytest.raises(InvalidWallpaperError):
        use_case.execute(
            WallpaperSettings(), monitor="DP-1", image_path=tmp_path / "nope.jpg"
        )
    assert not (tmp_path / "settings" / "wallpaper.json").exists()


def test_extension_no_soportada_rechazada(tmp_path):
    archivo = tmp_path / "doc.pdf"
    archivo.write_text("x")
    use_case = make_use_case(tmp_path, FakeBridge())

    with pytest.raises(InvalidWallpaperError):
        use_case.execute(WallpaperSettings(), monitor="DP-1", image_path=archivo)


def test_path_que_corrompe_hyprlang_no_escribe_nada(tmp_path):
    bridge = FakeBridge()
    use_case = make_use_case(tmp_path, bridge)
    malo = tmp_path / "pic##v2.jpg"
    malo.write_bytes(b"x")

    with pytest.raises(InvalidWallpaperError):
        use_case.execute(WallpaperSettings(), monitor="DP-1", image_path=malo)

    assert not (tmp_path / "settings" / "wallpaper.json").exists()
    assert not (tmp_path / "hyprpaper.conf").exists()


def test_fallo_de_ipc_propaga_dejando_estado_persistido(tmp_path, image):
    @dataclass
    class ExplodingBridge(FakeBridge):
        def set_wallpaper(self, monitor, image_path):
            raise HyprlandUnavailableError("ipc caído")

    use_case = make_use_case(tmp_path, ExplodingBridge())

    with pytest.raises(HyprlandUnavailableError):
        use_case.execute(WallpaperSettings(), monitor="DP-1", image_path=image)

    # contrato deliberado v1: lo persistido queda; la UI muestra el error
    assert (tmp_path / "settings" / "wallpaper.json").exists()
    assert (tmp_path / "hyprpaper.conf").exists()
