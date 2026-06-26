from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.animations import (  # noqa: E402
    BEZIER_CHOICES,
    AnimationLeaf,
    AnimationsSettings,
)
from ajustes.core.apply_animations import ApplyAnimations  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import HyprlandUnavailableError  # noqa: E402
from ajustes.core.hyprland_bridge import HyprctlBridge  # noqa: E402

from ajustes.config import SETTINGS_DIR  # noqa: E402

SPEED_MIN, SPEED_MAX, SPEED_STEP = 0.1, 50.0, 0.5


class _LeafForm:
    """Adw.ExpanderRow para una animación: switch de activado + speed/bezier/style."""

    def __init__(self, leaf: AnimationLeaf, on_change):
        self._name = leaf.name
        self.row = Adw.ExpanderRow(
            title=leaf.name,
            show_enable_switch=True,
            enable_expansion=leaf.enabled,
        )
        self.row.connect("notify::enable-expansion", lambda *_: on_change())

        self._speed = Adw.SpinRow.new_with_range(SPEED_MIN, SPEED_MAX, SPEED_STEP)
        self._speed.set_title("Velocidad")
        self._speed.set_subtitle("Decisegundos — menor = más rápido")
        self._speed.set_digits(1)
        self._speed.set_value(leaf.speed)
        self._speed.connect("notify::value", lambda *_: on_change())

        self._bezier = Adw.ComboRow(title="Curva (bezier)")
        model = Gtk.StringList()
        for name in BEZIER_CHOICES:
            model.append(name)
        self._bezier.set_model(model)
        if leaf.bezier in BEZIER_CHOICES:
            self._bezier.set_selected(BEZIER_CHOICES.index(leaf.bezier))
        self._bezier.connect("notify::selected", lambda *_: on_change())

        self._style = Adw.EntryRow(title="Estilo (opcional, ej. «popin 80%»)")
        self._style.set_text(leaf.style)
        self._style.connect("changed", lambda *_: on_change())

        for child in (self._speed, self._bezier, self._style):
            self.row.add_row(child)

    def current_leaf(self) -> AnimationLeaf:
        idx = self._bezier.get_selected()
        bezier = BEZIER_CHOICES[idx] if 0 <= idx < len(BEZIER_CHOICES) else "default"
        return AnimationLeaf(
            name=self._name,
            enabled=self.row.get_enable_expansion(),
            speed=self._speed.get_value(),
            bezier=bezier,
            style=self._style.get_text().strip(),
        )


class AnimationsPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Animaciones")
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = HyprctlBridge()
        self._apply = ApplyAnimations(store=self._store, bridge=self._bridge)
        self._dirty = False
        self._forms: list[_LeafForm] = []
        self.set_child(self._build())

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
        group = Adw.PreferencesGroup(
            title="Animaciones individuales",
            description="Requiere que las animaciones estén activadas en Apariencia.",
        )
        for leaf in saved.leaves:
            form = _LeafForm(leaf, self._mark_dirty)
            self._forms.append(form)
            group.add(form.row)
        box.append(group)

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

    def _load_saved(self) -> AnimationsSettings:
        try:
            return AnimationsSettings.from_dict(self._store.read("animations") or {})
        except (ValueError, TypeError):
            return AnimationsSettings.defaults()

    def _mark_dirty(self):
        self._dirty = True
        self._save_btn.set_sensitive(True)

    def _current_settings(self) -> AnimationsSettings:
        return AnimationsSettings(leaves=tuple(f.current_leaf() for f in self._forms))

    def _on_restore_backup(self, _banner):
        try:
            restored = self._store.restore_latest_backup("animations")
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

    def _on_confirm(self, _dialog, response: str, settings: AnimationsSettings):
        if response != "apply":
            return
        try:
            self._apply.execute(settings)
            self._dirty = False
            self._save_btn.set_sensitive(False)
            self._error_banner.set_revealed(False)
            root = self.get_root()
            if root and hasattr(root, "add_toast"):
                root.add_toast(Adw.Toast(title="Animaciones actualizadas"))
        except (OSError, HyprlandUnavailableError, ValueError) as exc:
            self._error_banner.set_title(f"Error al aplicar: {exc}")
            self._error_banner.set_revealed(True)
