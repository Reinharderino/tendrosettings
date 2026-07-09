from ajustes.core.search import SettingEntry

MODULE_ID = "workspaces"

ENTRIES = [
    SettingEntry(
        label="Workspaces",
        keywords=("workspace", "escritorio", "espacio", "spaces", "pantalla", "monitor"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Asignar workspace a monitor",
        keywords=("asignar", "workspace", "monitor", "pantalla", "persistente", "fijo"),
        module_id=MODULE_ID,
    ),
]
