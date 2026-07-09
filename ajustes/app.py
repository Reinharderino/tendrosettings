import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, Gtk  # noqa: E402

from ajustes.config import APP_ID, APP_TITLE  # noqa: E402
from ajustes.core.search import search_entries  # noqa: E402
from ajustes.modules import wallpaper as wallpaper_module  # noqa: E402
from ajustes.modules import appearance as appearance_module  # noqa: E402
from ajustes.modules import keybindings as keybindings_module  # noqa: E402
from ajustes.modules import monitors as monitors_module  # noqa: E402
from ajustes.modules import workspaces as workspaces_module  # noqa: E402
from ajustes.modules import snapshots as snapshots_module  # noqa: E402
from ajustes.modules import grub as grub_module  # noqa: E402
from ajustes.modules import dualboot as dualboot_module  # noqa: E402
from ajustes.modules import credentials as credentials_module  # noqa: E402

# (module_id, título, subtítulo, icono, activo)
MODULE_CARDS = [
    (wallpaper_module.MODULE_ID, "Wallpaper", "Fondo por monitor", "preferences-desktop-wallpaper-symbolic", True),
    (appearance_module.MODULE_ID, "Apariencia", "Gaps, bordes, blur y colores", "preferences-desktop-theme-symbolic", True),
    (keybindings_module.MODULE_ID, "Keybindings", "Atajos de teclado", "input-keyboard-symbolic", True),
    (monitors_module.MODULE_ID, "Monitores", "Resolución y energía", "video-display-symbolic", True),
    (workspaces_module.MODULE_ID, "Workspaces", "Asignar a monitores", "view-grid-symbolic", True),
    (snapshots_module.MODULE_ID, "Snapshots", "Crear y borrar snapshots", "document-open-recent-symbolic", True),
    (grub_module.MODULE_ID, "GRUB", "Flags del kernel (cmdline)", "application-x-firmware-symbolic", True),
    (dualboot_module.MODULE_ID, "Dualboot", "Arranque entre sistemas", "computer-symbolic", True),
    (credentials_module.MODULE_ID, "Credenciales", "Llavero, SSH, GPG y TLS", "dialog-password-symbolic", True),
    ("autostart", "Autostart", "Próximamente", "system-run-symbolic", False),
]


class AjustesWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application):
        super().__init__(application=application, title=APP_TITLE)
        self.set_default_size(760, 560)
        self._all_entries = [*wallpaper_module.ENTRIES, *appearance_module.ENTRIES,
                             *keybindings_module.ENTRIES, *monitors_module.ENTRIES,
                             *workspaces_module.ENTRIES,
                             *snapshots_module.ENTRIES, *grub_module.ENTRIES,
                             *dualboot_module.ENTRIES, *credentials_module.ENTRIES]

        self._navigation = Adw.NavigationView()
        self.set_content(self._navigation)
        self._navigation.push(self._build_launcher_page())

    def _build_launcher_page(self) -> Adw.NavigationPage:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                          margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        self._search_entry = Gtk.SearchEntry(placeholder_text="Buscar un ajuste (ej. «fondo», «gif»)…")
        self._search_entry.connect("search-changed", self._on_search_changed)
        content.append(self._search_entry)

        self._results_list = Gtk.ListBox(css_classes=["boxed-list"], visible=False)
        self._results_list.connect("row-activated", self._on_result_activated)
        content.append(self._results_list)

        self._cards_flowbox = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            max_children_per_line=3, min_children_per_line=2,
            row_spacing=12, column_spacing=12,
        )
        for module_id, title, subtitle, icon_name, enabled in MODULE_CARDS:
            self._cards_flowbox.append(self._build_card(module_id, title, subtitle, icon_name, enabled))
        content.append(self._cards_flowbox)

        toolbar_view.set_content(Gtk.ScrolledWindow(child=content, vexpand=True))
        return Adw.NavigationPage(title="Ajustes", child=toolbar_view, tag="launcher")

    def _build_card(self, module_id, title, subtitle, icon_name, enabled) -> Gtk.Button:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      margin_top=18, margin_bottom=18)
        box.append(Gtk.Image(icon_name=icon_name, pixel_size=48))
        box.append(Gtk.Label(label=title, css_classes=["title-4"]))
        box.append(Gtk.Label(label=subtitle, css_classes=["dim-label", "caption"]))
        card = Gtk.Button(child=box, css_classes=["card"], sensitive=enabled)
        card.connect("clicked", lambda _button: self._open_module(module_id))
        return card

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        query = entry.get_text()
        self._results_list.remove_all()
        matches = search_entries(self._all_entries, query) if query.strip() else []
        self._results_list.set_visible(bool(matches))
        self._cards_flowbox.set_visible(not matches)
        for setting in matches:
            row = Adw.ActionRow(title=setting.label, subtitle=setting.module_id, activatable=True)
            row.setting_entry = setting
            self._results_list.append(row)

    def _on_result_activated(self, _list_box, row) -> None:
        self._open_module(row.setting_entry.module_id)

    def _open_module(self, module_id: str) -> None:
        if module_id == wallpaper_module.MODULE_ID:
            from ajustes.modules.wallpaper.view import WallpaperPage

            self._navigation.push(WallpaperPage())
        elif module_id == appearance_module.MODULE_ID:
            from ajustes.modules.appearance.view import AppearancePage

            self._navigation.push(AppearancePage())
        elif module_id == keybindings_module.MODULE_ID:
            from ajustes.modules.keybindings.view import KeybindingsPage

            self._navigation.push(KeybindingsPage())
        elif module_id == monitors_module.MODULE_ID:
            from ajustes.modules.monitors.view import MonitorsPage

            self._navigation.push(MonitorsPage())
        elif module_id == workspaces_module.MODULE_ID:
            from ajustes.modules.workspaces.view import WorkspacesPage

            self._navigation.push(WorkspacesPage())
        elif module_id == snapshots_module.MODULE_ID:
            from ajustes.modules.snapshots.view import SnapshotsPage

            self._navigation.push(SnapshotsPage())
        elif module_id == grub_module.MODULE_ID:
            from ajustes.modules.grub.view import GrubPage

            self._navigation.push(GrubPage())
        elif module_id == dualboot_module.MODULE_ID:
            from ajustes.modules.dualboot.view import DualbootPage

            self._navigation.push(DualbootPage())
        elif module_id == credentials_module.MODULE_ID:
            from ajustes.modules.credentials.view import CredentialsPage

            self._navigation.push(CredentialsPage())


class AjustesApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_activate(self):
        window = self.get_active_window() or AjustesWindow(application=self)
        window.present()


def main() -> int:
    return AjustesApplication().run(None)
