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
        [LUA, "tests/lua/keybindings_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def test_keybindings_registra_validos_y_omite_invalidos_con_aviso(tmp_path):
    (tmp_path / "keybindings.json").write_text(json.dumps({"binds": [
        {"id": "k1", "mods": ["SUPER", "SHIFT"], "key": "B",
         "action": {"type": "exec", "command": "firefox"}, "enabled": True},
        {"id": "k2", "mods": ["SUPER"], "key": "3",
         "action": {"type": "dispatcher", "name": "goto_workspace", "arg": "3"},
         "enabled": True},
        {"id": "k3", "mods": ["SUPER", "CTRL"], "key": "H",
         "action": {"type": "dispatcher", "name": "focus_direction", "arg": "left"},
         "enabled": True},
        {"id": "k4", "mods": ["SUPER"], "key": "T",
         "action": {"type": "dispatcher", "name": "toggle_float", "arg": ""},
         "enabled": True},
        # inválidos: fuera de lista blanca, exec vacío, sin mods — se omiten con aviso
        {"id": "k5", "mods": ["SUPER"], "key": "X",
         "action": {"type": "dispatcher", "name": "hackear_nasa", "arg": ""},
         "enabled": True},
        {"id": "k6", "mods": ["SUPER"], "key": "Y",
         "action": {"type": "exec", "command": ""}, "enabled": True},
        {"id": "k7", "mods": [], "key": "Z",
         "action": {"type": "exec", "command": "ls"}, "enabled": True},
        # deshabilitado: se salta sin aviso
        {"id": "k8", "mods": ["SUPER"], "key": "W",
         "action": {"type": "exec", "command": "ls"}, "enabled": False},
    ]}), encoding="utf-8")

    result = run_spec(tmp_path, "mixed")

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
    assert "omitido" in result.stdout  # los inválidos se avisan, no se silencian


def test_keybindings_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "keybindings.json").write_text("{rotísimo", encoding="utf-8")

    result = run_spec(tmp_path, "vacio")

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_keybindings_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "vacio")

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
