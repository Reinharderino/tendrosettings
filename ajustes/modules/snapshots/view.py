from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.errors import SnapshotError  # noqa: E402
from ajustes.core.snapshot_bridge import SnapperBridge  # noqa: E402
from ajustes.core.snapshots import Snapshot, read_snapshots  # noqa: E402

from ajustes.config import SNAPSHOTS_DIR  # noqa: E402


class SnapshotsPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Snapshots")
        self._bridge = SnapperBridge()
        self._checks: dict[int, Gtk.CheckButton] = {}
        self.set_child(self._build())
        self._refresh()

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        # --- Crear ---
        create_group = Adw.PreferencesGroup(title="Crear snapshot")
        self._desc_row = Adw.EntryRow(title="Descripción")
        create_btn = Gtk.Button(
            label="Crear", css_classes=["suggested-action"], valign=Gtk.Align.CENTER,
        )
        create_btn.connect("clicked", self._on_create)
        self._desc_row.add_suffix(create_btn)
        create_group.add(self._desc_row)
        box.append(create_group)

        # --- Banner de error/aviso ---
        self._error_banner = Adw.Banner(title="", revealed=False)
        box.append(self._error_banner)

        # --- Lista de snapshots (se rellena en _refresh) ---
        self._list_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(self._list_holder)

        # --- Borrar seleccionados ---
        self._delete_btn = Gtk.Button(
            label="Borrar seleccionados",
            css_classes=["destructive-action", "pill"],
            sensitive=False, halign=Gtk.Align.CENTER, margin_top=6,
        )
        self._delete_btn.connect("clicked", self._on_delete_clicked)
        box.append(self._delete_btn)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=box, vexpand=True))
        return toolbar_view

    # ---------- lista ----------

    def _refresh(self):
        child = self._list_holder.get_first_child()
        while child is not None:
            self._list_holder.remove(child)
            child = self._list_holder.get_first_child()
        self._checks.clear()

        snapshots = read_snapshots(SNAPSHOTS_DIR)
        if not snapshots:
            self._list_holder.append(Adw.StatusPage(
                title="Sin snapshots",
                description="No se encontraron snapshots en /.snapshots.",
                icon_name="document-open-recent-symbolic",
            ))
            self._delete_btn.set_sensitive(False)
            return

        group = Adw.PreferencesGroup(
            title="Snapshots existentes",
            description="Marca los que quieras borrar.",
        )
        for snap in snapshots:
            group.add(self._build_row(snap))
        self._list_holder.append(group)
        self._update_delete_sensitivity()

    def _build_row(self, snap: Snapshot) -> Adw.ActionRow:
        subtitle = snap.date
        if snap.cleanup:
            subtitle += f" · cleanup: {snap.cleanup}"
        row = Adw.ActionRow(
            title=f"#{snap.num} · {snap.type} — {snap.description or '(sin descripción)'}",
            subtitle=subtitle,
        )
        check = Gtk.CheckButton(valign=Gtk.Align.CENTER)
        check.connect("toggled", lambda *_: self._update_delete_sensitivity())
        row.add_prefix(check)
        row.set_activatable_widget(check)
        self._checks[snap.num] = check
        return row

    def _selected_nums(self) -> list[int]:
        return [num for num, check in self._checks.items() if check.get_active()]

    def _update_delete_sensitivity(self):
        self._delete_btn.set_sensitive(bool(self._selected_nums()))

    # ---------- acciones ----------

    def _on_create(self, _btn):
        description = self._desc_row.get_text().strip()
        try:
            num = self._bridge.create_snapshot(description)
        except SnapshotError as exc:
            self._show_error(str(exc))
            return
        self._desc_row.set_text("")
        self._error_banner.set_revealed(False)
        self._toast(f"Snapshot #{num} creado")
        self._refresh()

    def _on_delete_clicked(self, _btn):
        nums = self._selected_nums()
        if not nums:
            return
        listing = ", ".join(f"#{n}" for n in sorted(nums, reverse=True))
        dialog = Adw.AlertDialog(
            heading="Borrar snapshots",
            body=f"Se borrarán permanentemente: {listing}. Esto no se puede deshacer. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Borrar")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_confirm, nums)
        dialog.present(self)

    def _on_delete_confirm(self, _dialog, response: str, nums: list[int]):
        if response != "delete":
            return
        try:
            self._bridge.delete_snapshots(nums)
        except SnapshotError as exc:
            self._show_error(str(exc))
            return
        self._error_banner.set_revealed(False)
        self._toast(f"Borrados {len(nums)} snapshot(s)")
        self._refresh()

    def _show_error(self, message: str):
        self._error_banner.set_title(message)
        self._error_banner.set_revealed(True)

    def _toast(self, message: str):
        root = self.get_root()
        if root and hasattr(root, "add_toast"):
            root.add_toast(Adw.Toast(title=message))
