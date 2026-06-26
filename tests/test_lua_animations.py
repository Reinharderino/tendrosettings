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
        [LUA, "tests/lua/animations_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


VALID_JSON = {
    "animations": [
        {"name": "windows", "enabled": True, "speed": 7.0, "bezier": "myBezier", "style": ""},
        {"name": "windowsOut", "enabled": True, "speed": 7.0, "bezier": "default", "style": "popin 80%"},
        {"name": "fade", "enabled": False, "speed": 4.0, "bezier": "linear", "style": ""},
    ]
}


def test_animations_aplica_leaves(tmp_path):
    (tmp_path / "animations.json").write_text(json.dumps(VALID_JSON), encoding="utf-8")
    result = run_spec(tmp_path, "valid")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_animations_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_animations_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "animations.json").write_text("{corrupto", encoding="utf-8")
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
