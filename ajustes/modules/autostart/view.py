import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.apply_autostart import ApplyAutostart  # noqa: E402
from ajustes.core.autostart import AutostartEntry, AutostartSettings  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402

from ajustes.config import SETTINGS_DIR  # noqa: E402


class AutostartPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Autostart")
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._apply = ApplyAutostart(store=self._store)
        self._rows: list = []   # cada Adw.ActionRow guarda ._command y ._switch
        self.set_child(self._build())

    def _load_saved(self) -> AutostartSettings:
        try:
            return AutostartSettings.from_dict(self._store.read("autostart") or {})
        except (ValueError, TypeError):
            return AutostartSettings(entries=())

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                            margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        self._box.append(Adw.Banner(
            title="Los cambios se aplican al próximo inicio de sesión.",
            revealed=True,
        ))

        # Alta de comando
        add_group = Adw.PreferencesGroup(title="Agregar comando")
        self._command_entry = Adw.EntryRow(title="Comando…")
        add_btn = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER,
                             tooltip_text="Agregar")
        add_btn.connect("clicked", self._on_add)
        self._command_entry.add_suffix(add_btn)
        add_group.add(self._command_entry)
        self._box.append(add_group)

        # Lista de entradas
        self._list_group = Adw.PreferencesGroup(title="Al iniciar sesión")
        self._box.append(self._list_group)

        self._save_btn = Gtk.Button(
            label="Guardar cambios",
            css_classes=["suggested-action", "pill"],
            sensitive=False, halign=Gtk.Align.CENTER, margin_top=12,
        )
        self._save_btn.connect("clicked", self._on_save)
        self._box.append(self._save_btn)

        for entry in self._load_saved().entries:
            self._append_row(entry)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=self._box, vexpand=True))
        return toolbar_view

    def _append_row(self, entry: AutostartEntry):
        row = Adw.ActionRow(title=entry.command)
        switch = Gtk.Switch(active=entry.enabled, valign=Gtk.Align.CENTER)
        switch.connect("notify::active", lambda *_: self._mark_dirty())
        delete_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["flat"], tooltip_text="Borrar")
        delete_btn.connect("clicked", self._on_delete, row)
        row.add_suffix(switch)
        row.add_suffix(delete_btn)
        row._command = entry.command   # referencia para reconstruir settings al guardar
        row._switch = switch
        self._list_group.add(row)
        self._rows.append(row)

    def _on_add(self, _btn):
        command = self._command_entry.get_text().strip()
        if not command:
            return
        self._append_row(AutostartEntry(command=command, enabled=True))
        self._command_entry.set_text("")
        self._mark_dirty()

    def _on_delete(self, _btn, row):
        self._list_group.remove(row)
        self._rows.remove(row)
        self._mark_dirty()

    def _mark_dirty(self):
        self._save_btn.set_sensitive(True)

    def _current_settings(self) -> AutostartSettings:
        entries = tuple(
            AutostartEntry(command=row._command, enabled=row._switch.get_active())
            for row in self._rows
        )
        # from_dict re-valida (descarta comandos vacíos) antes de persistir
        return AutostartSettings.from_dict(AutostartSettings(entries=entries).to_dict())

    def _on_save(self, _btn):
        self._apply.execute(self._current_settings())
        self._save_btn.set_sensitive(False)
        root = self.get_root()
        if root and hasattr(root, "add_toast"):
            root.add_toast(Adw.Toast(title="Autostart guardado — se aplica al próximo inicio"))
