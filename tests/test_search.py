from ajustes.core.search import SettingEntry, search_entries

ENTRIES = [
    SettingEntry(label="Wallpaper por monitor", keywords=("fondo", "monitor"), module_id="wallpaper"),
    SettingEntry(label="Carpetas de imágenes", keywords=("galería", "carpeta"), module_id="wallpaper"),
]


def test_busca_por_label_sin_distinguir_mayusculas():
    assert search_entries(ENTRIES, "WALLPAPER") == [ENTRIES[0]]


def test_busca_por_keyword():
    assert search_entries(ENTRIES, "galería") == [ENTRIES[1]]


def test_query_vacia_devuelve_todo():
    assert search_entries(ENTRIES, "  ") == ENTRIES
