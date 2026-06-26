from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.apply_grub_settings import ApplyGrubSettings  # noqa: E402
from ajustes.core.dualboot import EfiBootState, build_bootorder  # noqa: E402
from ajustes.core.dualboot_bridge import EfibootmgrBridge  # noqa: E402
from ajustes.core.errors import DualBootError, GrubError  # noqa: E402
from ajustes.core.grub import read_grub_key  # noqa: E402
from ajustes.core.grub_bridge import RealGrubBridge  # noqa: E402

from ajustes.config import BACKUPS_DIR, DEFAULT_GRUB  # noqa: E402

TIMEOUT_MAX = 60


class DualbootPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Dualboot")
        self._bridge = EfibootmgrBridge()
        self._grub_apply = ApplyGrubSettings(
            bridge=RealGrubBridge(), default_grub_path=DEFAULT_GRUB, backups_dir=BACKUPS_DIR,
        )
        self._radios: dict[str, Gtk.CheckButton] = {}
        self._state: EfiBootState | None = None
        self.set_child(self._build())

    # ---------- carga ----------

    def _load_state(self) -> EfiBootState | None:
        try:
            return self._bridge.read_state()
        except DualBootError:
            return None

    def _read_grub_defaults(self) -> tuple[int, bool]:
        """Devuelve (timeout, os_prober_activo) desde /etc/default/grub."""
        try:
            content = DEFAULT_GRUB.read_text(encoding="utf-8")
        except OSError:
            return 5, True
        timeout_raw = read_grub_key(content, "GRUB_TIMEOUT") or "5"
        timeout = int(timeout_raw) if timeout_raw.isdigit() else 5
        os_prober = (read_grub_key(content, "GRUB_DISABLE_OS_PROBER") or "false") != "true"
        return timeout, os_prober

    # ---------- construcción ----------

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        box.append(Adw.Banner(
            title="Gestiona el arranque entre sistemas. Los cambios piden autenticación.",
            revealed=True,
        ))

        self._error_banner = Adw.Banner(title="", revealed=False)

        self._state = self._load_state()
        box.append(self._build_os_group())
        box.append(self._build_actions())
        box.append(self._build_grub_group())
        box.append(self._error_banner)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=box, vexpand=True))
        return toolbar_view

    def _build_os_group(self) -> Gtk.Widget:
        group = Adw.PreferencesGroup(
            title="Sistemas operativos (UEFI)",
            description="Selecciona uno para las acciones de abajo.",
        )
        if self._state is None or not self._state.order:
            group.add(Adw.ActionRow(
                title="No se pudieron leer las entradas de arranque",
                subtitle="¿efibootmgr disponible y firmware UEFI?",
            ))
            return group

        labels = {e.num: e.label for e in self._state.entries}
        first_radio: Gtk.CheckButton | None = None
        for num in self._state.order:
            label = labels.get(num, f"Entrada {num}")
            is_current = num == self._state.current
            row = Adw.ActionRow(
                title=label + ("  ●" if is_current else ""),
                subtitle=f"id {num}" + (" · actual" if is_current else ""),
            )
            radio = Gtk.CheckButton(valign=Gtk.Align.CENTER)
            if first_radio is None:
                first_radio = radio
            else:
                radio.set_group(first_radio)
            if is_current:
                radio.set_active(True)
            row.add_prefix(radio)
            row.set_activatable_widget(radio)
            self._radios[num] = radio
            group.add(row)
        # Si ninguna es la actual, marca la primera
        if self._state.current not in self._radios and first_radio is not None:
            first_radio.set_active(True)
        return group

    def _build_actions(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      halign=Gtk.Align.CENTER, margin_top=6)
        self._bootnext_btn = Gtk.Button(
            label="Arrancar la próxima vez", css_classes=["suggested-action", "pill"],
        )
        self._bootnext_btn.connect("clicked", self._on_boot_next)
        self._default_btn = Gtk.Button(label="Fijar por defecto", css_classes=["pill"])
        self._default_btn.connect("clicked", self._on_set_default)
        enabled = bool(self._radios)
        self._bootnext_btn.set_sensitive(enabled)
        self._default_btn.set_sensitive(enabled)
        box.append(self._bootnext_btn)
        box.append(self._default_btn)
        return box

    def _build_grub_group(self) -> Adw.PreferencesGroup:
        timeout, os_prober = self._read_grub_defaults()
        group = Adw.PreferencesGroup(
            title="Menú GRUB",
            description="Requiere regenerar grub.cfg (update-grub) al aplicar.",
        )
        self._timeout_row = Adw.SpinRow.new_with_range(0, TIMEOUT_MAX, 1)
        self._timeout_row.set_title("Timeout del menú (s)")
        self._timeout_row.set_subtitle("0 = arranca de inmediato")
        self._timeout_row.set_value(timeout)

        self._osprober_row = Adw.SwitchRow(
            title="Detectar otros sistemas operativos",
            subtitle="os-prober: añade Windows y otros SO al menú de GRUB",
        )
        self._osprober_row.set_active(os_prober)

        apply_btn = Gtk.Button(
            label="Aplicar ajustes de GRUB",
            css_classes=["suggested-action"], valign=Gtk.Align.CENTER,
        )
        apply_btn.connect("clicked", self._on_apply_grub)
        apply_row = Adw.ActionRow(title="")
        apply_row.add_suffix(apply_btn)

        group.add(self._timeout_row)
        group.add(self._osprober_row)
        group.add(apply_row)
        return group

    # ---------- selección ----------

    def _selected_num(self) -> str | None:
        for num, radio in self._radios.items():
            if radio.get_active():
                return num
        return None

    def _selected_label(self) -> str:
        num = self._selected_num()
        if self._state and num:
            for e in self._state.entries:
                if e.num == num:
                    return e.label
        return num or "?"

    # ---------- acciones firmware ----------

    def _on_boot_next(self, _btn):
        num = self._selected_num()
        if not num:
            return
        label = self._selected_label()
        dialog = Adw.AlertDialog(
            heading="Arrancar la próxima vez",
            body=f"En el próximo reinicio se arrancará «{label}» (solo una vez). ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("ok", "Aplicar")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_boot_next_confirm, num, label)
        dialog.present(self)

    def _on_boot_next_confirm(self, _dialog, response: str, num: str, label: str):
        if response != "ok":
            return
        try:
            self._bridge.set_boot_next(num)
        except DualBootError as exc:
            self._show_error(str(exc))
            return
        self._error_banner.set_revealed(False)
        self._offer_reboot(label)

    def _offer_reboot(self, label: str):
        dialog = Adw.AlertDialog(
            heading="Reiniciar ahora",
            body=f"Listo: el próximo arranque será «{label}». ¿Reiniciar ahora?",
        )
        dialog.add_response("later", "Más tarde")
        dialog.add_response("reboot", "Reiniciar")
        dialog.set_response_appearance("reboot", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_reboot_confirm)
        dialog.present(self)

    def _on_reboot_confirm(self, _dialog, response: str):
        if response != "reboot":
            self._toast("Se arrancará el SO elegido en el próximo reinicio")
            return
        try:
            self._bridge.reboot()
        except DualBootError as exc:
            self._show_error(str(exc))

    def _on_set_default(self, _btn):
        num = self._selected_num()
        if not num or self._state is None:
            return
        label = self._selected_label()
        dialog = Adw.AlertDialog(
            heading="Fijar SO por defecto",
            body=f"«{label}» pasará a ser el primero en el orden de arranque UEFI. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("ok", "Aplicar")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_set_default_confirm, num, label)
        dialog.present(self)

    def _on_set_default_confirm(self, _dialog, response: str, num: str, label: str):
        if response != "ok":
            return
        try:
            self._bridge.set_boot_order(build_bootorder(self._state, num))
        except DualBootError as exc:
            self._show_error(str(exc))
            return
        self._error_banner.set_revealed(False)
        self._toast(f"«{label}» fijado como SO por defecto")

    # ---------- acciones GRUB ----------

    def _on_apply_grub(self, _btn):
        updates = {
            "GRUB_TIMEOUT": str(int(self._timeout_row.get_value())),
            "GRUB_DISABLE_OS_PROBER": "false" if self._osprober_row.get_active() else "true",
        }
        try:
            self._grub_apply.execute(updates)
        except (GrubError, OSError) as exc:
            self._show_error(str(exc))
            return
        self._error_banner.set_revealed(False)
        self._toast("Ajustes de GRUB aplicados")

    # ---------- helpers ----------

    def _show_error(self, message: str):
        self._error_banner.set_title(f"Error: {message}")
        self._error_banner.set_revealed(True)

    def _toast(self, message: str):
        root = self.get_root()
        if root and hasattr(root, "add_toast"):
            root.add_toast(Adw.Toast(title=message))
