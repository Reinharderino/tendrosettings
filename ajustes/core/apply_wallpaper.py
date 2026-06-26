from dataclasses import dataclass
from pathlib import Path

from ajustes.core.config_store import ConfigStore, backup_and_write
from ajustes.core.errors import InvalidWallpaperError
from ajustes.core.gallery import ANIMATED_EXTENSIONS, IMAGE_EXTENSIONS
from ajustes.core.hyprland_bridge import HyprlandBridge
from ajustes.core.wallpaper import (
    MonitorWallpaper,
    WallpaperSettings,
    generate_hyprpaper_conf,
)


@dataclass(frozen=True)
class ApplyResult:
    settings: WallpaperSettings
    applied_live: bool


class ApplyWallpaper:
    """Asigna una imagen a un monitor: valida → JSON → hyprpaper.conf → IPC."""

    def __init__(
        self,
        store: ConfigStore,
        bridge: HyprlandBridge,
        hyprpaper_conf_path: Path,
    ):
        self._store = store
        self._bridge = bridge
        self._hyprpaper_conf_path = hyprpaper_conf_path

    def execute(
        self, settings: WallpaperSettings, monitor: str, image_path: Path
    ) -> ApplyResult:
        self._validate(image_path)
        animated = image_path.suffix.lower() in ANIMATED_EXTENSIONS
        wallpaper = MonitorWallpaper(path=str(image_path), animated=animated)
        updated = settings.assign(monitor, wallpaper)
        # Generar ANTES de escribir: si el path corrompe hyprlang, no se persiste nada.
        # (generate_hyprpaper_conf excluye los animados, así que el gif no llega a hyprlang.)
        conf_content = generate_hyprpaper_conf(updated)
        self._store.write("wallpaper", updated.to_dict())
        backup_and_write(
            self._hyprpaper_conf_path,
            conf_content,
            backups_dir=self._store.backups_dir(),
        )
        applied_live = self._bridge.is_available()
        if applied_live:
            if animated:
                self._bridge.set_animated_wallpaper(
                    monitor, str(image_path), wallpaper.fit_mode
                )
            else:
                self._bridge.set_wallpaper(monitor, str(image_path))
        return ApplyResult(settings=updated, applied_live=applied_live)

    @staticmethod
    def _validate(image_path: Path) -> None:
        if not image_path.is_file():
            raise InvalidWallpaperError(f"no existe: {image_path}")
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS | ANIMATED_EXTENSIONS:
            raise InvalidWallpaperError(f"formato no soportado: {image_path.suffix}")
