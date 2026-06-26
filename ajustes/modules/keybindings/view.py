from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.apply_keybindings import ApplyKeybindings  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import AjustesError, BindConflictError, InvalidBindError  # noqa: E402
from ajustes.core.hyprland_bridge import HyprctlBridge  # noqa: E402
from ajustes.core.keybindings import (  # noqa: E402
    Bind,
    BindAction,
    CatalogBind,
    DIRECTIONS,
    DISPATCHERS,
    DISPATCHERS_BY_NAME,
    FORM_MODS,
    KeybindingsSettings,
    WORKSPACE_MAX,
    WORKSPACE_MIN,
    combo_label,
    parse_catalog,
    system_catalog,
)

from ajustes.config import SETTINGS_DIR  # noqa: E402

SPECIAL_KEYS = (
    *[f"F{i}" for i in range(1, 13)],
    "RETURN", "SPACE", "TAB", "ESCAPE", "BACKSPACE", "DELETE",
    "left", "right", "up", "down", "Home", "End", "Prior", "Next", "Print",
    "XF86AudioRaiseVolume", "XF86AudioLowerVolume", "XF86AudioMute",
    "XF86AudioPlay", "XF86AudioNext", "XF86AudioPrev",
)
KEY_MODE_CHAR = "Carácter…"
ACTION_MODES = ("Ejecutar comando", "Acción de ventana")


def action_label(action: BindAction) -> str:
    if action.type == "exec":
        return action.command
    spec = DISPATCHERS_BY_NAME.get(action.name)
    label = spec.label if spec else action.name
    return f"{label} {action.arg}".strip()


def catalog_subtitle(entry: CatalogBind) -> str:
    if entry.description:
        return entry.description
    if entry.is_lua:
        return "definido en hyprland.lua"
    return f"{entry.dispatcher} {entry.arg}".strip()


class KeybindingsPage(Adw.NavigationPage):
    def __init__(self):
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = HyprctlBridge()
        self._apply = ApplyKeybindings(store=self._store, bridge=self._bridge)
        self._corrupt_error: AjustesError | None = None
        try:
            self._settings = KeybindingsSettings.from_dict(self._store.read("keybindings"))
        except AjustesError as error:
            self._settings = KeybindingsSettings()
            self._corrupt_error = error
        self._catalog, self._catalog_warning = self._load_catalog()

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        self._toast_overlay = Adw.ToastOverlay(child=self._build_content())
        toolbar_view.set_content(self._toast_overlay)
        super().__init__(title="Keybindings", child=toolbar_view, tag="keybindings")

    # ---------- estado ----------

    def _load_catalog(self) -> tuple[list[CatalogBind], str | None]:
        if not self._bridge.is_available():
            return [], ("Sin sesión Hyprland: catálogo del sistema no disponible; "
                        "los cambios se aplicarán al entrar")
        try:
            return parse_catalog(self._bridge.get_binds()), None
        except AjustesError as error:
            return [], f"No se pudo leer el catálogo del sistema: {error}"

    # ---------- construcción ----------

    def _build_content(self) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                          margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)

        if self._catalog_warning:
            content.append(Adw.Banner(title=self._catalog_warning, revealed=True))

        if self._corrupt_error is not None:
            restore_banner = Adw.Banner(
                title="keybindings.json corrupto — usando valores por defecto",
                button_label="Restaurar backup",
                revealed=True,
            )
            restore_banner.connect("button-clicked", self._on_restore_backup)
            content.append(restore_banner)

        content.append(self._build_own_group())
        content.append(self._build_system_group())
        return Gtk.ScrolledWindow(child=content, vexpand=True)

    def _build_own_group(self) -> Adw.PreferencesGroup:
        self._own_group = Adw.PreferencesGroup(
            title="Mis atajos",
            description="Creados por la app — viven en keybindings.json",
        )
        add_button = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["flat"], tooltip_text="Nuevo atajo")
        add_button.connect("clicked", self._on_add_clicked)
        self._own_group.set_header_suffix(add_button)
        self._own_rows: list[Adw.ActionRow] = []
        self._reload_own_rows()
        return self._own_group

    def _build_system_group(self) -> Adw.PreferencesGroup:
        self._system_group = Adw.PreferencesGroup(
            title="Del sistema",
            description="Definidos en hyprland.lua — solo lectura",
        )
        self._system_rows: list[Adw.ActionRow] = []
        self._reload_system_rows()
        return self._system_group

    # ---------- estado → UI ----------

    def _reload_own_rows(self) -> None:
        for row in self._own_rows:
            self._own_group.remove(row)
        self._own_rows = []
        for bind in self._settings.binds:
            row = Adw.ActionRow(title=combo_label(bind.mods, bind.key),
                                subtitle=self._own_subtitle(bind))

            switch = Gtk.Switch(active=bind.enabled, valign=Gtk.Align.CENTER,
                                tooltip_text="Activado")
            switch.connect("state-set", self._on_enabled_changed, bind.id)
            row.add_suffix(switch)

            edit_button = Gtk.Button(icon_name="document-edit-symbolic",
                                     valign=Gtk.Align.CENTER, css_classes=["flat"],
                                     tooltip_text="Editar")
            edit_button.connect("clicked", self._on_edit_clicked, bind.id)
            row.add_suffix(edit_button)

            delete_button = Gtk.Button(icon_name="user-trash-symbolic",
                                       valign=Gtk.Align.CENTER, css_classes=["flat"],
                                       tooltip_text="Eliminar")
            delete_button.connect("clicked", self._on_delete_clicked, bind.id)
            row.add_suffix(delete_button)

            self._own_group.add(row)
            self._own_rows.append(row)

    def _reload_system_rows(self) -> None:
        for row in self._system_rows:
            self._system_group.remove(row)
        self._system_rows = []
        for entry in system_catalog(self._catalog, self._settings):
            row = Adw.ActionRow(title=combo_label(entry.mods, entry.key),
                                subtitle=catalog_subtitle(entry))
            row.add_suffix(Gtk.Image(icon_name="changes-prevent-symbolic",
                                     tooltip_text="Solo lectura"))
            self._system_group.add(row)
            self._system_rows.append(row)

    def _own_subtitle(self, bind: Bind) -> str:
        label = action_label(bind.action)
        return f"{label} — {bind.description}" if bind.description else label

    def _refresh_lists(self) -> None:
        self._reload_own_rows()
        self._reload_system_rows()

    # ---------- handlers ----------

    def _on_add_clicked(self, _button) -> None:
        BindDialog(bind=None, bind_id=self._settings.next_id(),
                   on_save=self._save_bind).present(self)

    def _on_edit_clicked(self, _button, bind_id: str) -> None:
        bind = next(b for b in self._settings.binds if b.id == bind_id)
        BindDialog(bind=bind, bind_id=bind_id, on_save=self._save_bind).present(self)

    def _save_bind(self, bind: Bind) -> str | None:
        try:
            result = self._apply.save(self._settings, bind, self._catalog)
        except BindConflictError as error:
            clash = error.conflicting
            detail = (self._own_subtitle(clash) if isinstance(clash, Bind)
                      else catalog_subtitle(clash))
            return (f"{combo_label(bind.mods, bind.key)} ya está en uso: "
                    f"{detail}")
        except InvalidBindError as error:
            return str(error)
        except (AjustesError, OSError) as error:
            return f"no se pudo guardar: {error}"
        self._settings = result.settings
        self._refresh_lists()
        self._toast_overlay.add_toast(
            Adw.Toast(title=self._saved_message("Atajo guardado", result))
        )
        return None

    def _on_delete_clicked(self, _button, bind_id: str) -> None:
        dialog = Adw.AlertDialog(
            heading="¿Eliminar el atajo?",
            body="Se quitará de keybindings.json y dejará de funcionar tras recargar.",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Eliminar")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_response, bind_id)
        dialog.present(self)

    def _on_delete_response(self, _dialog, response: str, bind_id: str) -> None:
        if response != "delete":
            return
        try:
            result = self._apply.delete(self._settings, bind_id)
        except (AjustesError, OSError) as error:
            self._toast_overlay.add_toast(Adw.Toast(title=str(error)))
            return
        self._settings = result.settings
        self._refresh_lists()
        self._toast_overlay.add_toast(Adw.Toast(title=self._saved_message("Atajo eliminado", result)))

    def _on_enabled_changed(self, _switch, state: bool, bind_id: str) -> bool:
        try:
            result = self._apply.set_enabled(self._settings, bind_id, state)
        except (AjustesError, OSError) as error:
            self._toast_overlay.add_toast(Adw.Toast(title=str(error)))
            return True
        self._settings = result.settings
        return False

    def _on_restore_backup(self, banner: Adw.Banner) -> None:
        if not self._store.restore_latest_backup("keybindings"):
            self._toast_overlay.add_toast(Adw.Toast(title="No hay backups que restaurar"))
            return
        try:
            self._settings = KeybindingsSettings.from_dict(self._store.read("keybindings"))
        except AjustesError as error:
            self._toast_overlay.add_toast(Adw.Toast(title=f"Backup corrupto: {error}"))
            return
        banner.set_revealed(False)
        self._refresh_lists()
        self._toast_overlay.add_toast(Adw.Toast(title="Backup restaurado"))

    @staticmethod
    def _saved_message(prefix: str, result) -> str:
        if result.applied_live:
            return f"{prefix} (recargado en vivo)"
        return f"{prefix} (se aplicará al entrar a Hyprland)"


class BindDialog(Adw.Dialog):
    """Alta y edición comparten el formulario; valida al guardar.

    No persiste por sí mismo: construye el Bind y delega en el callback
    `on_save(bind) -> str | None` (None = éxito; str = error inline).
    """

    def __init__(self, bind: Bind | None, bind_id: str, on_save):
        super().__init__(title="Editar atajo" if bind else "Nuevo atajo",
                         content_width=440)
        self._bind_id = bind_id
        self._on_save = on_save
        self._enabled = bind.enabled if bind else True

        page = Adw.PreferencesPage()
        page.add(self._build_combo_group(bind))
        page.add(self._build_action_group(bind))
        page.add(self._build_footer_group(bind))

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar(show_start_title_buttons=False,
                               show_end_title_buttons=False)
        cancel_button = Gtk.Button(label="Cancelar")
        cancel_button.connect("clicked", lambda _b: self.close())
        header.pack_start(cancel_button)
        save_button = Gtk.Button(label="Guardar", css_classes=["suggested-action"])
        save_button.connect("clicked", self._on_save_clicked)
        header.pack_end(save_button)
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(page)
        self.set_child(toolbar_view)

    # ---------- grupos ----------

    def _build_combo_group(self, bind: Bind | None) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Combinación")

        mods_row = Adw.ActionRow(title="Modificadores")
        mods_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        active_mods = set(bind.mods) if bind else set()
        self._mod_buttons: dict[str, Gtk.ToggleButton] = {}
        for mod in FORM_MODS:
            button = Gtk.ToggleButton(label=mod.capitalize(),
                                      active=mod in active_mods)
            self._mod_buttons[mod] = button
            mods_box.append(button)
        mods_row.add_suffix(mods_box)
        group.add(mods_row)

        keys = [KEY_MODE_CHAR, *SPECIAL_KEYS]
        self._key_combo = Adw.ComboRow(title="Tecla especial",
                                       model=Gtk.StringList.new(keys))
        self._key_entry = Adw.EntryRow(title="Tecla (un carácter)")
        if bind:
            if bind.key in SPECIAL_KEYS:
                self._key_combo.set_selected(keys.index(bind.key))
            else:
                self._key_entry.set_text(bind.key)
        self._key_combo.connect("notify::selected", self._on_key_mode_changed)
        group.add(self._key_combo)
        group.add(self._key_entry)
        self._on_key_mode_changed(self._key_combo, None)
        return group

    def _build_action_group(self, bind: Bind | None) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Acción")
        is_dispatcher = bind is not None and bind.action.type == "dispatcher"

        self._mode_combo = Adw.ComboRow(title="Tipo",
                                        model=Gtk.StringList.new(list(ACTION_MODES)))
        self._mode_combo.set_selected(1 if is_dispatcher else 0)
        self._mode_combo.connect("notify::selected", self._on_action_mode_changed)
        group.add(self._mode_combo)

        self._command_entry = Adw.EntryRow(title="Comando")
        if bind and bind.action.type == "exec":
            self._command_entry.set_text(bind.action.command)
        group.add(self._command_entry)

        labels = [spec.label for spec in DISPATCHERS]
        self._dispatcher_combo = Adw.ComboRow(title="Acción de ventana",
                                              model=Gtk.StringList.new(labels))
        if is_dispatcher:
            names = [spec.name for spec in DISPATCHERS]
            if bind.action.name in names:
                self._dispatcher_combo.set_selected(names.index(bind.action.name))
        self._dispatcher_combo.connect("notify::selected", self._on_action_mode_changed)
        group.add(self._dispatcher_combo)

        self._workspace_row = Adw.SpinRow.new_with_range(WORKSPACE_MIN, WORKSPACE_MAX, 1)
        self._workspace_row.set_title("Workspace")
        self._direction_combo = Adw.ComboRow(title="Dirección",
                                             model=Gtk.StringList.new(list(DIRECTIONS)))
        if is_dispatcher and bind.action.arg:
            if bind.action.arg.isdigit():
                self._workspace_row.set_value(int(bind.action.arg))
            elif bind.action.arg in DIRECTIONS:
                self._direction_combo.set_selected(DIRECTIONS.index(bind.action.arg))
        group.add(self._workspace_row)
        group.add(self._direction_combo)

        self._on_action_mode_changed(self._mode_combo, None)
        return group

    def _build_footer_group(self, bind: Bind | None) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        self._description_entry = Adw.EntryRow(title="Descripción (opcional)")
        if bind:
            self._description_entry.set_text(bind.description)
        group.add(self._description_entry)
        self._error_label = Gtk.Label(css_classes=["error"], wrap=True,
                                      visible=False, xalign=0,
                                      margin_top=6, margin_start=12)
        group.add(self._error_label)
        return group

    # ---------- visibilidad contextual ----------

    def _on_key_mode_changed(self, combo, _param) -> None:
        self._key_entry.set_visible(combo.get_selected() == 0)

    def _on_action_mode_changed(self, _widget, _param) -> None:
        exec_mode = self._mode_combo.get_selected() == 0
        self._command_entry.set_visible(exec_mode)
        self._dispatcher_combo.set_visible(not exec_mode)
        spec = DISPATCHERS[self._dispatcher_combo.get_selected()]
        self._workspace_row.set_visible(not exec_mode and spec.arg_kind == "workspace")
        self._direction_combo.set_visible(not exec_mode and spec.arg_kind == "direction")

    # ---------- guardado ----------

    def _selected_key(self) -> str:
        selected = self._key_combo.get_selected()
        if selected > 0:
            return SPECIAL_KEYS[selected - 1]
        return self._key_entry.get_text().strip()

    def _build_action(self) -> BindAction:
        if self._mode_combo.get_selected() == 0:
            return BindAction(type="exec", command=self._command_entry.get_text().strip())
        spec = DISPATCHERS[self._dispatcher_combo.get_selected()]
        arg = ""
        if spec.arg_kind == "workspace":
            arg = str(int(self._workspace_row.get_value()))
        elif spec.arg_kind == "direction":
            arg = DIRECTIONS[self._direction_combo.get_selected()]
        return BindAction(type="dispatcher", name=spec.name, arg=arg)

    def _on_save_clicked(self, _button) -> None:
        key = self._selected_key()
        if len(key) > 1 and key not in SPECIAL_KEYS:
            self._show_error("la tecla debe ser un carácter o una especial de la lista")
            return
        bind = Bind(
            id=self._bind_id,
            mods=tuple(mod for mod, button in self._mod_buttons.items()
                       if button.get_active()),
            key=key,
            action=self._build_action(),
            description=self._description_entry.get_text().strip(),
            enabled=self._enabled,
        )
        error = self._on_save(bind)
        if error:
            self._show_error(error)
            return
        self.close()

    def _show_error(self, message: str) -> None:
        self._error_label.set_label(message)
        self._error_label.set_visible(True)
