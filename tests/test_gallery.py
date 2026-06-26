import os

import pytest

from ajustes.core.gallery import GalleryImage, scan_folders


def test_escanea_imagenes_y_marca_animadas(tmp_path):
    (tmp_path / "b.jpg").write_bytes(b"x")
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "anim.gif").write_bytes(b"x")
    (tmp_path / "notas.txt").write_text("no soy imagen")

    images = scan_folders([str(tmp_path)])

    assert [img.path.name for img in images] == ["a.png", "anim.gif", "b.jpg"]
    assert [img.animated for img in images] == [False, True, False]


def test_carpeta_inexistente_se_ignora(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")

    images = scan_folders([str(tmp_path / "no_existe"), str(tmp_path)])

    assert len(images) == 1


def test_expande_tilde(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "casa.webp").write_bytes(b"x")

    images = scan_folders(["~"])

    assert images[0].path.name == "casa.webp"


def test_carpeta_sin_permisos_se_ignora(tmp_path):
    bloqueada = tmp_path / "bloqueada"
    bloqueada.mkdir()
    (tmp_path / "visible.jpg").write_bytes(b"x")
    os.chmod(bloqueada, 0o000)
    try:
        images = scan_folders([str(bloqueada), str(tmp_path)])
    finally:
        os.chmod(bloqueada, 0o755)

    assert [img.path.name for img in images] == ["visible.jpg"]


def test_carpetas_duplicadas_no_duplican_resultados(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")

    images = scan_folders([str(tmp_path), str(tmp_path)])

    assert len(images) == 1
