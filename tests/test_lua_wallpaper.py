import json
import os
import pathlib
import shutil
import subprocess

import pytest

LUA = shutil.which("lua")
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(LUA is None, reason="no hay intérprete lua en el sistema")


def run_spec(tmp_path, case):
    return subprocess.run(
        [LUA, "tests/lua/wallpaper_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def write_wallpaper(tmp_path, monitors):
    (tmp_path / "wallpaper.json").write_text(
        json.dumps({"folders": ["~/Imágenes"], "monitors": monitors}), encoding="utf-8"
    )


def test_wallpaper_aplica_monitor_animado(tmp_path):
    write_wallpaper(
        tmp_path,
        {
            "DP-2": {
                "path": "/home/tendro/Vídeos/Hidamari/Maiden.gif",
                "fit_mode": "contain",
                "animated": True,
            }
        },
    )
    result = run_spec(tmp_path, "animated")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_wallpaper_ignora_estaticos(tmp_path):
    write_wallpaper(
        tmp_path,
        {"DP-1": {"path": "/img/a.png", "fit_mode": "cover", "animated": False}},
    )
    result = run_spec(tmp_path, "static_only")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_wallpaper_mixto_solo_aplica_animado(tmp_path):
    write_wallpaper(
        tmp_path,
        {
            "DP-1": {"path": "/img/a.png", "fit_mode": "cover", "animated": False},
            "DP-2": {"path": "/v/Maiden.gif", "fit_mode": "cover", "animated": True},
        },
    )
    result = run_spec(tmp_path, "mixed")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_wallpaper_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_wallpaper_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "wallpaper.json").write_text("{corrupto", encoding="utf-8")
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
