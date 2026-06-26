from ajustes.core.search import SettingEntry

MODULE_ID = "monitors"

ENTRIES = [
    SettingEntry(
        label="Monitores",
        keywords=("monitor", "pantalla", "resolución", "escala", "hz", "pantallas"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Tasa de refresco",
        keywords=("refresco", "hz", "fps", "144", "60", "120"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Energía de pantalla",
        keywords=("dpms", "energía", "suspender", "apagar", "pantalla", "ahorro"),
        module_id=MODULE_ID,
    ),
]
