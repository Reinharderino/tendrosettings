from dataclasses import dataclass
from pathlib import Path

from ajustes.core.app_colors import (
    AppColorsSettings,
    generate_color_scheme,
    is_dark,
    nearest_gnome_accent,
)
from ajustes.core.config_store import ConfigStore, backup_and_write, timestamped_backup
from ajustes.core.theming_bridge import ThemingBridge

# Nombre fijo del esquema que gestiona la app (sobreescribe el suyo en cada apply).
SCHEME_NAME = "HyprAjustes"


@dataclass(frozen=True)
class ApplyResult:
    settings: AppColorsSettings
    synced_gtk: bool


class ApplyAppColors:
    """Aplica colores de texto/fondo/acento a las apps KDE/Qt (Dolphin++) y GTK.

    Genera un esquema .colors, lo aplica con plasma-apply-colorscheme (que escribe
    kdeglobals y refresca apps abiertas) y, opcionalmente, sincroniza GTK por gsettings.
    kdeglobals se respalda antes de tocarlo (lo modifica plasma-apply-colorscheme).
    """

    def __init__(
        self,
        store: ConfigStore,
        bridge: ThemingBridge,
        schemes_dir: Path,
        kdeglobals_path: Path,
    ):
        self._store = store
        self._bridge = bridge
        self._schemes_dir = schemes_dir
        self._kdeglobals_path = kdeglobals_path

    def execute(self, settings: AppColorsSettings) -> ApplyResult:
        self._store.write("app_colors", settings.to_dict())

        # Respaldo de kdeglobals antes de que plasma-apply-colorscheme lo modifique.
        timestamped_backup(self._kdeglobals_path, self._store.backups_dir())

        content = generate_color_scheme(
            settings.text_color, settings.background_color,
            settings.accent_color, SCHEME_NAME,
        )
        self._schemes_dir.mkdir(parents=True, exist_ok=True)
        backup_and_write(
            self._schemes_dir / f"{SCHEME_NAME}.colors",
            content,
            backups_dir=self._store.backups_dir(),
        )

        self._bridge.apply_kde_scheme(SCHEME_NAME)

        synced_gtk = settings.sync_gtk
        if synced_gtk:
            self._bridge.apply_gtk(
                prefer_dark=is_dark(settings.background_color),
                accent_name=nearest_gnome_accent(settings.accent_color),
            )

        return ApplyResult(settings=settings, synced_gtk=synced_gtk)
