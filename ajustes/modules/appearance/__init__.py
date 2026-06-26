from ajustes.core.search import SettingEntry

MODULE_ID = "appearance"

ENTRIES = [
    SettingEntry(
        label="Apariencia",
        keywords=("apariencia", "tema", "look", "feel", "estilo"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Espaciado y bordes",
        keywords=("gaps", "espaciado", "borde", "border", "márgenes"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Redondeo y blur",
        keywords=("rounding", "redondeo", "blur", "desenfoque", "esquinas"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Colores de borde",
        keywords=("color", "colores", "borde", "gradiente", "activo", "inactivo"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Animaciones",
        keywords=("animaciones", "animations", "transiciones"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Colores de aplicaciones",
        keywords=("colores", "texto", "apps", "dolphin", "kde", "qt", "gtk", "tema", "kdeglobals"),
        module_id=MODULE_ID,
    ),
]
