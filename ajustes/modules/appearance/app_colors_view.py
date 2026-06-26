import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ajustes.core.app_colors import AppColorsSettings, normalize_hex  # noqa: E402
from ajustes.core.apply_app_colors import ApplyAppColors  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import ThemingError  # noqa: E402
from ajustes.core.theming_bridge import KdeGtkBridge  # noqa: E402

from ajustes.config import KDEGLOBALS, SCHEMES_DIR, SETTINGS_DIR  # noqa: E402


class _HexColorRow:
    """Adw.ActionRow con Gtk.ColorDialogButton para un color #rrggbb opaco."""

    def __init__(self, title: str, hex_color: str, on_change):
        self._button = Gtk.ColorDialogButton(
            dialog=Gtk.ColorDialog(with_alpha=False),
            valign=Gtk.Align.CENTER,
        )
        rgba = Gdk.RGBA()
        rgba.parse(normalize_hex(hex_color) or "#000000")
        self._button.set_rgba(rgba)
        self._button.connect("notify::rgba", lambda *_: on_change())
        self.row = Adw.ActionRow(title=title)
        self.row.add_suffix(self._button)

    def hex_color(self) -> str:
        c = self._button.get_rgba()
        return "#%02x%02x%02x" % (round(c.red * 255), round(c.green * 255), round(c.blue * 255))


class AppColorsPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Colores de aplicaciones")
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = KdeGtkBridge()
        self._apply = ApplyAppColors(
            store=self._store, bridge=self._bridge,
            schemes_dir=SCHEMES_DIR, kdeglobals_path=KDEGLOBALS,
        )
        self._dirty = False
        self.set_child(self._build())

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        saved = self._load_saved()

        group = Adw.PreferencesGroup(
            title="Colores de apps KDE/Qt y GTK",
            description="Aplica a Dolphin y demás apps del sistema vía esquema de color.",
        )
        self._text = _HexColorRow("Color de texto", saved.text_color, self._mark_dirty)
        self._background = _HexColorRow("Color de fondo", saved.background_color, self._mark_dirty)
        self._accent = _HexColorRow("Color de acento", saved.accent_color, self._mark_dirty)
        group.add(self._text.row)
        group.add(self._background.row)
        group.add(self._accent.row)

        self._sync_gtk = Adw.SwitchRow(
            title="Sincronizar apps GTK",
            subtitle="Claro/oscuro y acento más cercano vía gsettings",
        )
        self._sync_gtk.set_active(saved.sync_gtk)
        self._sync_gtk.connect("notify::active", lambda *_: self._mark_dirty())
        group.add(self._sync_gtk)
        box.append(group)

        # Bajo Hyprland, las apps Qt sólo aplican kdeglobals si cargan el platform
        # theme de KDE (QT_QPA_PLATFORMTHEME=kde). Si falta, los colores KDE/Qt no
        # se verán aunque se escriban; se avisa en vez de fallar en silencio.
        if os.environ.get("QT_QPA_PLATFORMTHEME") != "kde":
            box.append(Adw.Banner(
                title="Falta QT_QPA_PLATFORMTHEME=kde: las apps Qt no aplicarán estos "
                      "colores hasta reiniciar la sesión de Hyprland.",
                revealed=True,
            ))

        self._info_banner = Adw.Banner(
            title="Cambia los colores de todas las apps KDE/Qt. kdeglobals se respalda antes.",
            revealed=True,
        )
        box.append(self._info_banner)

        self._error_banner = Adw.Banner(title="", revealed=False)
        box.append(self._error_banner)

        self._save_btn = Gtk.Button(
            label="Aplicar a las aplicaciones",
            css_classes=["suggested-action", "pill"],
            sensitive=False, halign=Gtk.Align.CENTER, margin_top=12,
        )
        self._save_btn.connect("clicked", self._on_save_clicked)
        box.append(self._save_btn)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=box, vexpand=True))
        return toolbar_view

    def _load_saved(self) -> AppColorsSettings:
        try:
            return AppColorsSettings.from_dict(self._store.read("app_colors") or {})
        except (ValueError, TypeError):
            return AppColorsSettings.defaults()

    def _mark_dirty(self):
        self._dirty = True
        self._save_btn.set_sensitive(True)

    def _current_settings(self) -> AppColorsSettings:
        return AppColorsSettings(
            text_color=self._text.hex_color(),
            background_color=self._background.hex_color(),
            accent_color=self._accent.hex_color(),
            sync_gtk=self._sync_gtk.get_active(),
        )

    def _on_save_clicked(self, _btn):
        settings = self._current_settings()
        dialog = Adw.AlertDialog(
            heading="Aplicar colores a las aplicaciones",
            body="Cambiará los colores de las apps KDE/Qt (Dolphin, etc.)"
                 + (" y GTK" if settings.sync_gtk else "")
                 + ". kdeglobals se respalda antes. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_confirm, settings)
        dialog.present(self)

    def _on_confirm(self, _dialog, response: str, settings: AppColorsSettings):
        if response != "apply":
            return
        try:
            self._apply.execute(settings)
            self._dirty = False
            self._save_btn.set_sensitive(False)
            self._error_banner.set_revealed(False)
            root = self.get_root()
            if root and hasattr(root, "add_toast"):
                root.add_toast(Adw.Toast(title="Colores aplicados a las aplicaciones"))
        except (OSError, ThemingError) as exc:
            self._error_banner.set_title(f"Error al aplicar: {exc}")
            self._error_banner.set_revealed(True)
