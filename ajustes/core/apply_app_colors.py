import configparser
import io
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


def merge_scheme_into_kdeglobals(
    scheme_content: str, kdeglobals_content: str, scheme_name: str
) -> str:
    """Inyecta los grupos [Colors:*] del esquema en un kdeglobals existente.

    Las apps Qt/KDE leen la paleta de kdeglobals, NO del .colors. En una máquina
    con Plasma eso lo hacía `plasma-apply-colorscheme`; sin Plasma ese binario no
    existe y el .colors quedaba huérfano: Dolphin seguía con la paleta anterior
    (texto del tema nuevo sobre fondo del viejo = ilegible).

    Sólo se tocan los grupos de color y `[General] ColorScheme`. Todo lo demás
    (widgetStyle, fuentes, BrowserApplication, atajos) se conserva: kdeglobals es
    de KDE, no nuestro, y pisarlo entero borraría ajustes del usuario.
    """
    # Raw: los valores de kdeglobals traen '%' (atajos, rutas) que la
    # interpolación de configparser interpretaría como sintaxis y rompería.
    def parser() -> configparser.RawConfigParser:
        cfg = configparser.RawConfigParser(strict=False)
        cfg.optionxform = str  # kdeglobals distingue mayúsculas en las claves
        return cfg

    scheme = parser()
    scheme.read_string(scheme_content)

    merged = parser()
    if kdeglobals_content:
        merged.read_string(kdeglobals_content)

    for section in scheme.sections():
        if not section.startswith("Colors:"):
            continue
        merged[section] = dict(scheme[section])

    if not merged.has_section("General"):
        merged.add_section("General")
    merged["General"]["ColorScheme"] = scheme_name
    # El hash lo calcula Plasma para detectar esquemas editados a mano. Sin Plasma
    # nadie lo valida y uno viejo sólo confunde a quien lea el archivo.
    merged["General"].pop("ColorSchemeHash", None)

    out = io.StringIO()
    merged.write(out, space_around_delimiters=False)
    return out.getvalue()


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

        # kdeglobals es lo que leen de verdad las apps Qt: se escribe acá, no en
        # el bridge, que sólo avisa a las apps ya abiertas si Plasma está.
        kdeglobals_before = (
            self._kdeglobals_path.read_text(encoding="utf-8")
            if self._kdeglobals_path.exists()
            else ""
        )
        backup_and_write(
            self._kdeglobals_path,
            merge_scheme_into_kdeglobals(content, kdeglobals_before, SCHEME_NAME),
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
