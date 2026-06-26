from ajustes.core.search import SettingEntry

MODULE_ID = "snapshots"

ENTRIES = [
    SettingEntry(
        label="Snapshots",
        keywords=("snapshot", "snapshots", "snapper", "btrfs", "instantánea",
                  "respaldo", "copia", "restaurar"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Crear snapshot",
        keywords=("crear", "nuevo", "snapshot", "snapper"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Borrar snapshots",
        keywords=("borrar", "eliminar", "limpiar", "snapshot", "snapper"),
        module_id=MODULE_ID,
    ),
]
