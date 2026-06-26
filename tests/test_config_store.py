import json

import pytest

from ajustes.core.config_store import ConfigStore
from ajustes.core.errors import CorruptSettingsError


@pytest.fixture
def store(tmp_path):
    return ConfigStore(settings_dir=tmp_path)


def test_read_devuelve_none_si_no_existe(store):
    assert store.read("wallpaper") is None


def test_read_devuelve_dict_si_json_valido(store, tmp_path):
    (tmp_path / "wallpaper.json").write_text(json.dumps({"folders": ["~/Imágenes"]}))

    assert store.read("wallpaper") == {"folders": ["~/Imágenes"]}


def test_read_lanza_corrupt_si_json_invalido(store, tmp_path):
    (tmp_path / "wallpaper.json").write_text("{esto no es json")

    with pytest.raises(CorruptSettingsError) as exc:
        store.read("wallpaper")
    assert "wallpaper.json" in str(exc.value)
    assert exc.value.file_path.name == "wallpaper.json"
    assert exc.value.reason


def test_read_lanza_corrupt_si_no_es_objeto(store, tmp_path):
    (tmp_path / "wallpaper.json").write_text("[1, 2]")

    with pytest.raises(CorruptSettingsError):
        store.read("wallpaper")


def test_read_lanza_corrupt_si_encoding_invalido(store, tmp_path):
    (tmp_path / "wallpaper.json").write_bytes(b'{"a": "\xe9"}')  # UTF-8 inválido

    with pytest.raises(CorruptSettingsError):
        store.read("wallpaper")


def test_write_crea_archivo_y_directorio(store, tmp_path):
    store.write("wallpaper", {"folders": []})

    assert json.loads((tmp_path / "wallpaper.json").read_text(encoding="utf-8")) == {"folders": []}


def test_write_hace_backup_del_contenido_anterior(store, tmp_path):
    store.write("wallpaper", {"v": 1})
    store.write("wallpaper", {"v": 2})

    backups = store.backups_for("wallpaper")
    assert len(backups) == 1
    assert json.loads(backups[0].read_text(encoding="utf-8")) == {"v": 1}


def test_write_rota_backups_conservando_diez(store):
    for version in range(12):
        store.write("wallpaper", {"v": version})

    backups = store.backups_for("wallpaper")
    assert len(backups) == 10
    # backups_for devuelve el más reciente primero
    assert json.loads(backups[0].read_text(encoding="utf-8")) == {"v": 10}


def test_restore_latest_backup_recupera_el_anterior(store):
    store.write("wallpaper", {"v": 1})
    store.write("wallpaper", {"v": 2})

    assert store.restore_latest_backup("wallpaper") is True
    assert store.read("wallpaper") == {"v": 1}


def test_restore_sin_backups_devuelve_false(store):
    assert store.restore_latest_backup("wallpaper") is False
