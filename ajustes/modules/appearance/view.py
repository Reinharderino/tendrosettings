from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from ajustes.core.appearance import (  # noqa: E402
    AppearanceSettings,
    hypr_color_to_rgba_floats,
    rgba_floats_to_hypr_color,
)
from ajustes.core.apply_appearance import ApplyAppearance  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import HyprlandUnavailableError  # noqa: E402
from ajustes.core.hyprland_bridge import HyprctlBridge  # noqa: E402

from ajustes.config import SETTINGS_DIR  # noqa: E402

GAPS_MAX = 100
BORDER_MAX = 20
ROUNDING_MAX = 50
BLUR_SIZE_MIN, BLUR_SIZE_MAX = 1, 20
BLUR_PASSES_MIN, BLUR_PASSES_MAX = 1, 10
ANGLE_MAX = 360


class _ColorRow:
    """Adw.ActionRow con un Gtk.ColorDialogButton para un color de Hyprland."""

    def __init__(self, title: str, hypr_color: str, on_change):
        self._button = Gtk.ColorDialogButton(
            dialog=Gtk.ColorDialog(with_alpha=True),
            valign=Gtk.Align.CENTER,
        )
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue, rgba.alpha = hypr_color_to_rgba_floats(hypr_color)
        self._button.set_rgba(rgba)
        self._button.connect("notify::rgba", lambda *_: on_change())

        self.row = Adw.ActionRow(title=title)
        self.row.add_suffix(self._button)

    def hypr_color(self) -> str:
        rgba = self._button.get_rgba()
        return rgba_floats_to_hypr_color(rgba.red, rgba.green, rgba.blue, rgba.alpha)


class AppearancePage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Apariencia")
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = HyprctlBridge()
        self._apply = ApplyAppearance(store=self._store, bridge=self._bridge)
        self._dirty = False
        self.set_child(self._build())

    # ---------- construcción ----------

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        if not self._bridge.is_available():
            box.append(Adw.Banner(
                title="Sin sesión Hyprland activa — los cambios se aplicarán al próximo inicio.",
                revealed=True,
            ))

        saved = self._load_saved()

        box.append(self._build_windows_group(saved))
        box.append(self._build_decoration_group(saved))
        box.append(self._build_animations_group(saved))
        box.append(self._build_colors_group(saved))
        box.append(self._build_apps_group())

        self._error_banner = Adw.Banner(
            title="", revealed=False, button_label="Restaurar backup",
        )
        self._error_banner.connect("button-clicked", self._on_restore_backup)
        box.append(self._error_banner)

        self._save_btn = Gtk.Button(
            label="Guardar cambios",
            css_classes=["suggested-action", "pill"],
            sensitive=False, halign=Gtk.Align.CENTER, margin_top=12,
        )
        self._save_btn.connect("clicked", self._on_save_clicked)
        box.append(self._save_btn)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=box, vexpand=True))
        return toolbar_view

    def _load_saved(self) -> AppearanceSettings:
        try:
            data = self._store.read("appearance") or {}
            return AppearanceSettings.from_dict(data)
        except (ValueError, TypeError):
            return AppearanceSettings.defaults()

    def _spin(self, title, low, high, value, subtitle=None) -> Adw.SpinRow:
        row = Adw.SpinRow.new_with_range(low, high, 1)
        row.set_title(title)
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_value(value)
        row.connect("notify::value", lambda *_: self._mark_dirty())
        return row

    def _build_windows_group(self, saved: AppearanceSettings) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Ventanas")
        self._gaps_in = self._spin("Gaps interiores", 0, GAPS_MAX, saved.gaps_in)
        self._gaps_out = self._spin("Gaps exteriores", 0, GAPS_MAX, saved.gaps_out)
        self._border_size = self._spin("Tamaño de borde", 0, BORDER_MAX, saved.border_size)
        for row in (self._gaps_in, self._gaps_out, self._border_size):
            group.add(row)
        return group

    def _build_decoration_group(self, saved: AppearanceSettings) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Decoración")
        self._rounding = self._spin("Redondeo (rounding)", 0, ROUNDING_MAX, saved.rounding)

        self._blur_enabled = Adw.SwitchRow(title="Blur (desenfoque)")
        self._blur_enabled.set_active(saved.blur_enabled)
        self._blur_enabled.connect("notify::active", lambda *_: self._mark_dirty())

        self._blur_size = self._spin("Tamaño del blur", BLUR_SIZE_MIN, BLUR_SIZE_MAX, saved.blur_size)
        self._blur_passes = self._spin("Pasadas del blur", BLUR_PASSES_MIN, BLUR_PASSES_MAX, saved.blur_passes)

        for row in (self._rounding, self._blur_enabled, self._blur_size, self._blur_passes):
            group.add(row)
        return group

    def _build_animations_group(self, saved: AppearanceSettings) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Animaciones")
        self._animations_enabled = Adw.SwitchRow(
            title="Animaciones",
            subtitle="Interruptor maestro de todas las animaciones",
        )
        self._animations_enabled.set_active(saved.animations_enabled)
        self._animations_enabled.connect("notify::active", lambda *_: self._mark_dirty())
        group.add(self._animations_enabled)

        configure_row = Adw.ActionRow(
            title="Configurar animaciones individuales",
            subtitle="Velocidad, curva y estilo por animación",
            activatable=True,
        )
        configure_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        configure_row.connect("activated", self._on_open_animations)
        group.add(configure_row)
        return group

    def _on_open_animations(self, _row):
        from ajustes.modules.appearance.animations_view import AnimationsPage

        nav = self.get_ancestor(Adw.NavigationView)
        if nav is not None:
            nav.push(AnimationsPage())

    def _build_apps_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Aplicaciones del sistema")
        row = Adw.ActionRow(
            title="Colores de aplicaciones",
            subtitle="Texto, fondo y acento para Dolphin y demás apps (KDE/Qt + GTK)",
            activatable=True,
        )
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", self._on_open_app_colors)
        group.add(row)
        return group

    def _on_open_app_colors(self, _row):
        from ajustes.modules.appearance.app_colors_view import AppColorsPage

        nav = self.get_ancestor(Adw.NavigationView)
        if nav is not None:
            nav.push(AppColorsPage())

    def _build_colors_group(self, saved: AppearanceSettings) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="Colores de borde",
            description="El borde activo es un gradiente entre dos colores.",
        )
        self._active_1 = _ColorRow("Borde activo · color 1", saved.active_color_1, self._mark_dirty)
        self._active_2 = _ColorRow("Borde activo · color 2", saved.active_color_2, self._mark_dirty)
        self._gradient_angle = self._spin("Ángulo del gradiente", 0, ANGLE_MAX, saved.gradient_angle)
        self._inactive = _ColorRow("Borde inactivo", saved.inactive_color, self._mark_dirty)
        group.add(self._active_1.row)
        group.add(self._active_2.row)
        group.add(self._gradient_angle)
        group.add(self._inactive.row)
        return group

    # ---------- estado ----------

    def _mark_dirty(self):
        self._dirty = True
        self._save_btn.set_sensitive(True)

    def _current_settings(self) -> AppearanceSettings:
        return AppearanceSettings(
            gaps_in=int(self._gaps_in.get_value()),
            gaps_out=int(self._gaps_out.get_value()),
            border_size=int(self._border_size.get_value()),
            rounding=int(self._rounding.get_value()),
            blur_enabled=self._blur_enabled.get_active(),
            blur_size=int(self._blur_size.get_value()),
            blur_passes=int(self._blur_passes.get_value()),
            animations_enabled=self._animations_enabled.get_active(),
            active_color_1=self._active_1.hypr_color(),
            active_color_2=self._active_2.hypr_color(),
            gradient_angle=int(self._gradient_angle.get_value()),
            inactive_color=self._inactive.hypr_color(),
        )

    # ---------- acciones ----------

    def _on_restore_backup(self, _banner):
        try:
            restored = self._store.restore_latest_backup("appearance")
            if not restored:
                self._error_banner.set_title("No hay backup disponible para restaurar.")
                self._error_banner.set_revealed(True)
                return
            if self._bridge.is_available():
                self._bridge.reload()
        except (OSError, HyprlandUnavailableError) as exc:
            self._error_banner.set_title(f"Error al restaurar: {exc}")
            self._error_banner.set_revealed(True)
            return
        self._error_banner.set_revealed(False)

    def _on_save_clicked(self, _btn):
        settings = self._current_settings()
        dialog = Adw.AlertDialog(
            heading="Aplicar cambios",
            body="La pantalla puede parpadear brevemente al recargar Hyprland. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_confirm, settings)
        dialog.present(self)

    def _on_confirm(self, _dialog, response: str, settings: AppearanceSettings):
        if response != "apply":
            return
        try:
            self._apply.execute(settings)
            self._dirty = False
            self._save_btn.set_sensitive(False)
            self._error_banner.set_revealed(False)
            root = self.get_root()
            if root and hasattr(root, "add_toast"):
                root.add_toast(Adw.Toast(title="Apariencia actualizada"))
        except (OSError, HyprlandUnavailableError, ValueError) as exc:
            self._error_banner.set_title(f"Error al aplicar: {exc}")
            self._error_banner.set_revealed(True)
