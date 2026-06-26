from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ajustes.core.apply_wallpaper import ApplyWallpaper  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import AjustesError  # noqa: E402
from ajustes.core.gallery import scan_folders  # noqa: E402
from ajustes.core.hyprland_bridge import HyprctlBridge  # noqa: E402
from ajustes.core.wallpaper import WallpaperSettings  # noqa: E402

from ajustes.config import HYPRPAPER_CONF, SETTINGS_DIR  # noqa: E402

THUMBNAIL_WIDTH = 192
THUMBNAIL_HEIGHT = 108
FALLBACK_MONITOR = "DP-1"


class WallpaperPage(Adw.NavigationPage):
    def __init__(self):
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = HyprctlBridge()
        self._apply_wallpaper = ApplyWallpaper(
            store=self._store, bridge=self._bridge, hyprpaper_conf_path=HYPRPAPER_CONF
        )
        self._corrupt_error: AjustesError | None = None
        try:
            self._settings = WallpaperSettings.from_dict(self._store.read("wallpaper"))
        except AjustesError as error:
            # JSON corrupto: defaults + banner que ofrece restaurar el último backup
            self._settings = WallpaperSettings()
            self._corrupt_error = error

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())
        self._toast_overlay = Adw.ToastOverlay(child=self._build_content())
        toolbar_view.set_content(self._toast_overlay)
        super().__init__(title="Wallpaper", child=toolbar_view, tag="wallpaper")

    # ---------- construcción ----------

    def _build_content(self) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                          margin_top=12, margin_bottom=24, margin_start=18, margin_end=18)

        if not self._bridge.is_available():
            content.append(Adw.Banner(
                title="Sin sesión Hyprland: los cambios se aplicarán al entrar", revealed=True
            ))

        if self._corrupt_error is not None:
            restore_banner = Adw.Banner(
                title="wallpaper.json corrupto — usando valores por defecto",
                button_label="Restaurar backup",
                revealed=True,
            )
            restore_banner.connect("button-clicked", self._on_restore_backup)
            content.append(restore_banner)

        content.append(self._build_target_group())
        content.append(self._build_gallery_group())
        content.append(self._build_folders_group())
        return Gtk.ScrolledWindow(child=content, vexpand=True)

    def _build_target_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Aplicar a")
        names = self._monitor_names()
        self._monitor_row = Adw.ComboRow(
            title="Monitor", model=Gtk.StringList.new(names)
        )
        group.add(self._monitor_row)

        animated_row = Adw.ActionRow(
            title="Wallpaper animado",
            subtitle="Los GIF se aplican vía swww automáticamente al elegirlos en la galería",
        )
        animated_row.add_prefix(
            Gtk.Image.new_from_icon_name("emblem-photos-symbolic")
        )
        group.add(animated_row)
        return group

    def _build_gallery_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="Galería",
            description="Clic en una imagen para aplicarla al monitor seleccionado",
        )
        self._gallery_flowbox = Gtk.FlowBox(
            selection_mode=Gtk.SelectionMode.NONE,
            max_children_per_line=4, min_children_per_line=2,
            row_spacing=8, column_spacing=8,
        )
        self._reload_gallery()
        group.add(self._gallery_flowbox)
        return group

    def _build_folders_group(self) -> Adw.PreferencesGroup:
        self._folders_group = Adw.PreferencesGroup(title="Carpetas de la galería")
        add_button = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["flat"])
        add_button.connect("clicked", self._on_add_folder)
        self._folders_group.set_header_suffix(add_button)
        self._folder_rows: list[Adw.ActionRow] = []
        self._reload_folder_rows()
        return self._folders_group

    # ---------- estado → UI ----------

    def _monitor_names(self) -> list[str]:
        if self._bridge.is_available():
            try:
                return self._bridge.monitor_names()
            except AjustesError:
                pass  # IPC caído pese a la signature: caer al JSON guardado
        return sorted(self._settings.monitors) or [FALLBACK_MONITOR]

    def _selected_monitor(self) -> str:
        return self._monitor_row.get_selected_item().get_string()

    def _reload_gallery(self) -> None:
        self._gallery_flowbox.remove_all()
        for image in scan_folders(self._settings.folders):
            if image.animated and image.path.suffix.lower() != ".gif":
                continue  # swww/awww solo anima GIF; vídeo (mp4/webm) necesitaría mpvpaper
            picture = Gtk.Picture.new_for_filename(str(image.path))
            picture.set_size_request(THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            button = Gtk.Button(child=picture, css_classes=["card"],
                                tooltip_text=image.path.name)
            button.connect("clicked", self._on_image_clicked, image.path)
            self._gallery_flowbox.append(button)

    def _reload_folder_rows(self) -> None:
        for row in self._folder_rows:
            self._folders_group.remove(row)
        self._folder_rows = []
        for folder in self._settings.folders:
            row = Adw.ActionRow(title=folder)
            remove_button = Gtk.Button(icon_name="user-trash-symbolic",
                                       valign=Gtk.Align.CENTER, css_classes=["flat"])
            remove_button.connect("clicked", self._on_remove_folder, folder)
            row.add_suffix(remove_button)
            self._folders_group.add(row)
            self._folder_rows.append(row)

    # ---------- handlers ----------

    def _on_image_clicked(self, _button, image_path: Path) -> None:
        try:
            result = self._apply_wallpaper.execute(
                self._settings, monitor=self._selected_monitor(), image_path=image_path
            )
        except (AjustesError, OSError) as error:
            self._toast_overlay.add_toast(Adw.Toast(title=str(error)))
            return
        self._settings = result.settings
        message = f"{image_path.name} → {self._selected_monitor()}"
        if not result.applied_live:
            message += " (se aplicará al entrar a Hyprland)"
        self._toast_overlay.add_toast(Adw.Toast(title=message))

    def _on_add_folder(self, _button) -> None:
        dialog = Gtk.FileDialog(title="Añadir carpeta de imágenes")
        dialog.select_folder(self.get_root(), None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog: Gtk.FileDialog, result) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error as error:
            if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return  # diálogo cancelado
            self._toast_overlay.add_toast(
                Adw.Toast(title=f"Error al elegir carpeta: {error.message}")
            )
            return
        self._update_folders([*self._settings.folders, folder.get_path()])

    def _on_remove_folder(self, _button, folder: str) -> None:
        self._update_folders([f for f in self._settings.folders if f != folder])

    def _on_restore_backup(self, banner: Adw.Banner) -> None:
        if not self._store.restore_latest_backup("wallpaper"):
            self._toast_overlay.add_toast(Adw.Toast(title="No hay backups que restaurar"))
            return
        try:
            self._settings = WallpaperSettings.from_dict(self._store.read("wallpaper"))
        except AjustesError as error:
            self._toast_overlay.add_toast(Adw.Toast(title=f"Backup corrupto: {error}"))
            return
        banner.set_revealed(False)
        self._reload_folder_rows()
        self._reload_gallery()
        self._toast_overlay.add_toast(Adw.Toast(title="Backup restaurado"))

    def _update_folders(self, folders: list[str]) -> None:
        new_settings = self._settings.with_folders(folders)
        try:
            self._store.write("wallpaper", new_settings.to_dict())
        except OSError as error:
            self._toast_overlay.add_toast(Adw.Toast(title=f"Error al guardar: {error}"))
            return
        self._settings = new_settings
        self._reload_folder_rows()
        self._reload_gallery()
