from ajustes.core.search import SettingEntry

MODULE_ID = "wallpaper"
MODULE_TITLE = "Wallpaper"

ENTRIES = [
    SettingEntry(
        label="Wallpaper por monitor",
        keywords=("fondo", "imagen", "monitor"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Carpetas de la galería",
        keywords=("galería", "carpeta", "imágenes"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Wallpaper animado",
        keywords=("gif", "vídeo", "animado", "swww"),
        module_id=MODULE_ID,
    ),
]
