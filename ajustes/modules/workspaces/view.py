import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.apply_workspaces import ApplyWorkspaces  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import HyprlandUnavailableError  # noqa: E402
from ajustes.core.hyprland_bridge import HyprctlBridge  # noqa: E402
from ajustes.core.workspaces import WorkspaceSettings, WorkspaceSpec  # noqa: E402

from ajustes.config import SETTINGS_DIR  # noqa: E402

WORKSPACE_COUNT = 10
UNASSIGNED = "Sin asignar"


class _WorkspaceRow:
    """Fila para un workspace: combo de monitor + switch persistente."""

    def __init__(self, number: int, monitors: list[str], saved: WorkspaceSpec | None, on_change):
        self._number = number
        self._monitors = monitors
        self._on_change = on_change

        self._combo = Adw.ComboRow(title=f"Workspace {number}")
        model = Gtk.StringList()
        model.append(UNASSIGNED)
        for name in monitors:
            model.append(name)
        self._combo.set_model(model)

        self._persistent = Gtk.Switch(valign=Gtk.Align.CENTER, tooltip_text="Persistente")
        self._combo.add_suffix(self._persistent)

        if saved and saved.monitor in monitors:
            self._combo.set_selected(monitors.index(saved.monitor) + 1)
            self._persistent.set_active(saved.persistent)

        self._combo.connect("notify::selected", lambda *_: on_change())
        self._persistent.connect("notify::active", lambda *_: on_change())

    def row(self) -> Adw.ComboRow:
        return self._combo

    def current_spec(self) -> WorkspaceSpec:
        idx = self._combo.get_selected()
        monitor = "" if idx <= 0 else self._monitors[idx - 1]
        return WorkspaceSpec(
            number=self._number,
            monitor=monitor,
            persistent=self._persistent.get_active(),
        )


class WorkspacesPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Workspaces")
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = HyprctlBridge()
        self._apply = ApplyWorkspaces(store=self._store, bridge=self._bridge)
        self._rows: list[_WorkspaceRow] = []
        self.set_child(self._build())

    def _monitor_names(self, saved: WorkspaceSettings) -> list[str]:
        try:
            names = self._bridge.monitor_names()
            if names:
                return names
        except HyprlandUnavailableError:
            pass
        # fallback: nombres guardados
        return sorted({w.monitor for w in saved.workspaces if w.monitor})

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

        saved_data = self._store.read("workspaces") or {}
        try:
            saved = WorkspaceSettings.from_dict(saved_data)
        except (ValueError, TypeError):
            saved = WorkspaceSettings(workspaces=())
        saved_by_number = {w.number: w for w in saved.workspaces}
        monitors = self._monitor_names(saved)

        group = Adw.PreferencesGroup(title="Asignación de workspaces a monitores")
        for number in range(1, WORKSPACE_COUNT + 1):
            row = _WorkspaceRow(number, monitors, saved_by_number.get(number), self._mark_dirty)
            self._rows.append(row)
            group.add(row.row())
        box.append(group)

        self._error_banner = Adw.Banner(title="", revealed=False, button_label="Restaurar backup")
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

    def _mark_dirty(self):
        self._save_btn.set_sensitive(True)

    def _on_restore_backup(self, _banner):
        try:
            restored = self._store.restore_latest_backup("workspaces")
            if restored and self._bridge.is_available():
                self._bridge.reload()
            if not restored:
                self._error_banner.set_title("No hay backup disponible para restaurar.")
                self._error_banner.set_revealed(True)
                return
        except (OSError, HyprlandUnavailableError) as exc:
            self._error_banner.set_title(f"Error al restaurar: {exc}")
            self._error_banner.set_revealed(True)
            return
        self._error_banner.set_revealed(False)

    def _on_save_clicked(self, _btn):
        specs = tuple(r.current_spec() for r in self._rows)
        settings = WorkspaceSettings(workspaces=specs)
        dialog = Adw.AlertDialog(
            heading="Aplicar cambios",
            body="La pantalla puede parpadear brevemente al recargar Hyprland. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_confirm, settings)
        dialog.present(self)

    def _on_confirm(self, _dialog, response: str, settings: WorkspaceSettings):
        if response != "apply":
            return
        try:
            self._apply.execute(settings)
            self._save_btn.set_sensitive(False)
            self._error_banner.set_revealed(False)
            root = self.get_root()
            if root and hasattr(root, "add_toast"):
                root.add_toast(Adw.Toast(title="Workspaces actualizados"))
        except (OSError, HyprlandUnavailableError, ValueError) as exc:
            self._error_banner.set_title(f"Error al aplicar: {exc}")
            self._error_banner.set_revealed(True)
