from collections.abc import Iterable
from dataclasses import dataclass, field

from ajustes.core.errors import InvalidWallpaperError

# hyprpaper 0.8: modos del bloque wallpaper{} que usa la UI v1.
FIT_MODES = ("cover", "contain")
DEFAULT_FIT_MODE = "cover"
DEFAULT_FOLDERS = ("~/Imágenes",)


@dataclass(frozen=True)
class MonitorWallpaper:
    path: str
    fit_mode: str = DEFAULT_FIT_MODE
    animated: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "MonitorWallpaper":
        return cls(
            # path vacío es válido aquí: la validación real (existencia, formato)
            # es responsabilidad del caso de uso ApplyWallpaper, no del modelo.
            path=str(data.get("path", "")),
            fit_mode=str(data.get("fit_mode", DEFAULT_FIT_MODE)),
            animated=bool(data.get("animated", False)),
        )

    def to_dict(self) -> dict:
        return {"path": self.path, "fit_mode": self.fit_mode, "animated": self.animated}


@dataclass(frozen=True)
class WallpaperSettings:
    """Inmutable por contrato: construir solo vía from_dict/assign/with_folders.

    `monitors` es un dict (mutable); ningún caller debe mutarlo tras construir.
    """

    folders: tuple[str, ...] = DEFAULT_FOLDERS
    monitors: dict[str, MonitorWallpaper] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict | None) -> "WallpaperSettings":
        if not data:
            return cls()
        monitors = {
            name: MonitorWallpaper.from_dict(raw)
            for name, raw in data.get("monitors", {}).items()
            if isinstance(raw, dict)
        }
        folders = tuple(str(f) for f in data.get("folders", DEFAULT_FOLDERS))
        return cls(folders=folders, monitors=monitors)

    def to_dict(self) -> dict:
        return {
            "folders": list(self.folders),
            "monitors": {name: mw.to_dict() for name, mw in self.monitors.items()},
        }

    def assign(self, monitor: str, wallpaper: MonitorWallpaper) -> "WallpaperSettings":
        return WallpaperSettings(
            folders=self.folders, monitors={**self.monitors, monitor: wallpaper}
        )

    def with_folders(self, folders: Iterable[str]) -> "WallpaperSettings":
        return WallpaperSettings(folders=tuple(folders), monitors=dict(self.monitors))


GENERATED_HEADER = (
    "# Generado por hypr-ajustes — NO editar a mano (se sobreescribe).\n"
    "# Los wallpapers animados no aparecen aquí: los maneja swww.\n"
)


def _hyprlang_safe(value: str) -> str:
    """hyprlang trunca en '##' (comentario inline) y trimea espacios de borde.

    No hay sintaxis de escape, así que esos valores se rechazan en vez de
    escribirse corruptos.
    """
    if "##" in value:
        raise InvalidWallpaperError(f"'##' rompe el parser de hyprlang: {value!r}")
    if value != value.strip():
        raise InvalidWallpaperError(
            f"hyprlang descarta espacios al inicio/final: {value!r}"
        )
    return value


def generate_hyprpaper_conf(settings: WallpaperSettings) -> str:
    blocks = [
        (
            "wallpaper {\n"
            f"    monitor = {_hyprlang_safe(name)}\n"
            f"    path = {_hyprlang_safe(mw.path)}\n"
            f"    fit_mode = {_hyprlang_safe(mw.fit_mode)}\n"
            "}"
        )
        for name, mw in sorted(settings.monitors.items())
        if not mw.animated
    ]
    conf = GENERATED_HEADER + "\nsplash = false\n"
    if blocks:
        conf += "\n" + "\n\n".join(blocks) + "\n"
    return conf
