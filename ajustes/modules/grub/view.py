from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.apply_grub import ApplyGrub  # noqa: E402
from ajustes.core.errors import GrubError  # noqa: E402
from ajustes.core.grub import (  # noqa: E402
    BOOT, COMPAT, GPU, PERF, POWER, SECURITY, STORAGE,
    CATALOG,
    BooleanFlag,
    ChoiceFlag,
    GrubFlags,
    add_custom_flag,
    build_cmdline,
    parse_cmdline,
    read_default_grub_value,
    remove_token,
)
from ajustes.core.grub_bridge import RealGrubBridge  # noqa: E402

from ajustes.config import BACKUPS_DIR, DEFAULT_GRUB  # noqa: E402

NONE_LABEL = "(desactivado)"
CATEGORY_ORDER = (BOOT, PERF, POWER, GPU, STORAGE, SECURITY, COMPAT)


class GrubPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="GRUB · Flags del kernel")
        self._apply = ApplyGrub(
            bridge=RealGrubBridge(),
            default_grub_path=DEFAULT_GRUB,
            backups_dir=BACKUPS_DIR,
        )
        self._updating = False
        self._bool_switches: dict[str, Adw.SwitchRow] = {}
        self._choice_combos: dict[str, tuple[Adw.ComboRow, tuple[str, ...]]] = {}
        self._load_error = False
        self._flags = self._load()
        self.set_child(self._build())
        self._render()

    # ---------- estado ----------

    def _load(self) -> GrubFlags:
        try:
            value = read_default_grub_value(DEFAULT_GRUB.read_text(encoding="utf-8")) or ""
            return parse_cmdline(value)
        except OSError:
            self._load_error = True
            return GrubFlags(frozenset(), {}, ())

    def _flags_from_widgets(self) -> GrubFlags:
        booleans = frozenset(
            token for token, sw in self._bool_switches.items() if sw.get_active()
        )
        choices: dict[str, str] = {}
        for key, (combo, values) in self._choice_combos.items():
            idx = combo.get_selected()
            if idx > 0:
                choices[key] = values[idx - 1]
        return GrubFlags(booleans, choices, self._flags.custom)

    def _set_flags(self, flags: GrubFlags) -> None:
        self._flags = flags
        self._render()
        self._mark_dirty()

    # ---------- construcción ----------

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        box.append(Adw.Banner(
            title="Cambia los parámetros de arranque del kernel. Se respalda "
                  "/etc/default/grub y los cambios requieren reiniciar.",
            revealed=True,
        ))
        if self._load_error:
            box.append(Adw.Banner(
                title="No se pudo leer /etc/default/grub — ¿usas GRUB?",
                revealed=True,
            ))

        box.append(self._build_chips_section())

        for category in CATEGORY_ORDER:
            box.append(self._build_category_group(category))

        self._error_banner = Adw.Banner(title="", revealed=False)
        box.append(self._error_banner)

        self._apply_btn = Gtk.Button(
            label="Aplicar (requiere reiniciar)",
            css_classes=["suggested-action", "pill"],
            sensitive=False, halign=Gtk.Align.CENTER, margin_top=6,
        )
        self._apply_btn.connect("clicked", self._on_apply_clicked)
        box.append(self._apply_btn)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=box, vexpand=True))
        return toolbar_view

    def _build_chips_section(self) -> Gtk.Widget:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        section.append(Gtk.Label(
            label="Flags activos — toca ✕ para quitar", xalign=0,
            css_classes=["heading"],
        ))
        self._chips_flow = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            column_spacing=6, row_spacing=6, homogeneous=False,
        )
        section.append(self._chips_flow)

        add_group = Adw.PreferencesGroup()
        self._custom_entry = Adw.EntryRow(
            title="Añadir flag (ej. «nvme.noacpi=1» o varios separados por espacio)",
            show_apply_button=True,
        )
        self._custom_entry.connect("apply", self._on_add_custom)
        add_group.add(self._custom_entry)
        section.append(add_group)

        self._preview = Gtk.Label(
            xalign=0, wrap=True, selectable=True,
            css_classes=["monospace", "dim-label"],
        )
        section.append(self._preview)
        return section

    def _build_category_group(self, category: str) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=category)
        for spec in CATALOG:
            if spec.category != category:
                continue
            if isinstance(spec, BooleanFlag):
                row = Adw.SwitchRow(title=spec.label, subtitle=self._subtitle(spec))
                row.connect("notify::active", self._on_widget_changed)
                self._bool_switches[spec.token] = row
                group.add(row)
            elif isinstance(spec, ChoiceFlag):
                row = Adw.ComboRow(title=spec.label, subtitle=self._subtitle(spec))
                model = Gtk.StringList()
                model.append(NONE_LABEL)
                for value in spec.values:
                    model.append(value)
                row.set_model(model)
                row.connect("notify::selected", self._on_widget_changed)
                self._choice_combos[spec.key] = (row, spec.values)
                group.add(row)
        return group

    @staticmethod
    def _subtitle(spec) -> str:
        return ("⚠ " + spec.description) if spec.risky else spec.description

    # ---------- render (estado -> widgets) ----------

    def _render(self) -> None:
        self._updating = True
        for token, sw in self._bool_switches.items():
            sw.set_active(token in self._flags.booleans)
        for key, (combo, values) in self._choice_combos.items():
            value = self._flags.choices.get(key)
            combo.set_selected(values.index(value) + 1 if value in values else 0)
        self._updating = False

        child = self._chips_flow.get_first_child()
        while child is not None:
            self._chips_flow.remove(child)
            child = self._chips_flow.get_first_child()

        tokens = build_cmdline(self._flags).split()
        for token in tokens:
            chip = Gtk.Button(label=f"{token}  ✕", css_classes=["pill"])
            chip.connect("clicked", self._on_chip_removed, token)
            self._chips_flow.append(chip)

        self._preview.set_text(build_cmdline(self._flags) or "(sin flags)")

    # ---------- handlers ----------

    def _on_widget_changed(self, *_):
        if self._updating:
            return
        self._set_flags(self._flags_from_widgets())

    def _on_chip_removed(self, _button, token: str):
        self._set_flags(remove_token(self._flags, token))

    def _on_add_custom(self, entry: Adw.EntryRow):
        text = entry.get_text().strip()
        if text:
            self._set_flags(add_custom_flag(self._flags, text))
            entry.set_text("")

    def _mark_dirty(self):
        if hasattr(self, "_apply_btn"):
            self._apply_btn.set_sensitive(not self._load_error)

    def _on_apply_clicked(self, _btn):
        new_cmdline = build_cmdline(self._flags)
        dialog = Adw.AlertDialog(
            heading="Aplicar flags de GRUB",
            body=f"Se escribirá /etc/default/grub (con backup) y se ejecutará "
                 f"update-grub.\n\nNuevo cmdline:\n{new_cmdline or '(vacío)'}\n\n"
                 f"Los cambios surten efecto tras reiniciar. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_apply_confirm, new_cmdline)
        dialog.present(self)

    def _on_apply_confirm(self, _dialog, response: str, new_cmdline: str):
        if response != "apply":
            return
        try:
            self._apply.execute(new_cmdline)
        except (GrubError, OSError) as exc:
            self._error_banner.set_title(f"Error: {exc}")
            self._error_banner.set_revealed(True)
            return
        self._error_banner.set_revealed(False)
        self._apply_btn.set_sensitive(False)
        root = self.get_root()
        if root and hasattr(root, "add_toast"):
            root.add_toast(Adw.Toast(title="GRUB actualizado — reinicia para aplicar"))
