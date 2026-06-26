import pytest

from ajustes.core.errors import InvalidWallpaperError
from ajustes.core.wallpaper import MonitorWallpaper, WallpaperSettings, generate_hyprpaper_conf


def test_defaults_sin_datos():
    settings = WallpaperSettings.from_dict(None)

    assert settings.folders == ("~/Imágenes",)
    assert settings.monitors == {}


def test_from_dict_tolerante_ignora_claves_desconocidas():
    settings = WallpaperSettings.from_dict(
        {
            "folders": ["/fondos"],
            "monitors": {"DP-1": {"path": "/fondos/a.jpg", "fit_mode": "contain"}},
            "clave_futura": 42,
        }
    )

    assert settings.folders == ("/fondos",)
    assert settings.monitors["DP-1"] == MonitorWallpaper(
        path="/fondos/a.jpg", fit_mode="contain"
    )


def test_roundtrip_to_dict_from_dict():
    original = WallpaperSettings(
        folders=("/fondos",),
        monitors={"DP-1": MonitorWallpaper(path="/fondos/a.jpg", animated=True)},
    )

    assert WallpaperSettings.from_dict(original.to_dict()) == original


def test_assign_devuelve_copia_actualizada():
    base = WallpaperSettings()

    updated = base.assign("DP-2", MonitorWallpaper(path="/fondos/b.png"))

    assert base.monitors == {}
    assert updated.monitors["DP-2"].path == "/fondos/b.png"


def test_with_folders_reemplaza_carpetas():
    updated = WallpaperSettings().with_folders(["/a", "/b"])

    assert updated.folders == ("/a", "/b")


def test_generador_emite_bloque_por_monitor():
    settings = WallpaperSettings(
        monitors={
            "DP-1": MonitorWallpaper(path="/fondos/a.jpg"),
            "DP-2": MonitorWallpaper(path="/fondos/b.png", fit_mode="contain"),
        }
    )

    conf = generate_hyprpaper_conf(settings)

    assert "splash = false" in conf
    assert (
        "wallpaper {\n    monitor = DP-1\n    path = /fondos/a.jpg\n"
        "    fit_mode = cover\n}" in conf
    )
    assert (
        "wallpaper {\n    monitor = DP-2\n    path = /fondos/b.png\n"
        "    fit_mode = contain\n}" in conf
    )


def test_generador_excluye_monitores_animados():
    settings = WallpaperSettings(
        monitors={"DP-1": MonitorWallpaper(path="/fondos/maiden.gif", animated=True)}
    )

    conf = generate_hyprpaper_conf(settings)

    assert "maiden.gif" not in conf
    assert "DP-1" not in conf


def test_generador_avisa_que_es_generado():
    assert "hypr-ajustes" in generate_hyprpaper_conf(WallpaperSettings())


def test_generador_rechaza_path_con_doble_almohadilla():
    settings = WallpaperSettings(
        monitors={"DP-1": MonitorWallpaper(path="/fondos/pic##v2.jpg")}
    )

    with pytest.raises(InvalidWallpaperError):
        generate_hyprpaper_conf(settings)


def test_generador_rechaza_path_con_espacios_en_los_bordes():
    settings = WallpaperSettings(
        monitors={"DP-1": MonitorWallpaper(path="/fondos/a.jpg ")}
    )

    with pytest.raises(InvalidWallpaperError):
        generate_hyprpaper_conf(settings)


def test_generador_acepta_rutas_con_espacios_y_no_ascii():
    settings = WallpaperSettings(
        monitors={"DP-1": MonitorWallpaper(path="/home/x/Imágenes/mi fondo.jpg")}
    )

    assert "path = /home/x/Imágenes/mi fondo.jpg" in generate_hyprpaper_conf(settings)


def test_generador_sin_monitores_emite_conf_minima_exacta():
    conf = generate_hyprpaper_conf(WallpaperSettings())

    assert conf == (
        "# Generado por hypr-ajustes — NO editar a mano (se sobreescribe).\n"
        "# Los wallpapers animados no aparecen aquí: los maneja swww.\n"
        "\n"
        "splash = false\n"
    )


def test_generador_separa_bloques_con_linea_en_blanco():
    settings = WallpaperSettings(
        monitors={
            "DP-1": MonitorWallpaper(path="/a.jpg"),
            "DP-2": MonitorWallpaper(path="/b.jpg"),
        }
    )

    assert "}\n\nwallpaper {" in generate_hyprpaper_conf(settings)
