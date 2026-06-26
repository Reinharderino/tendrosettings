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
        [LUA, "tests/lua/monitors_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


VALID_JSON = {
    "monitors": [
        {"name": "DP-1", "mode": "3440x1440@144.00Hz", "scale": 1.0,
         "x": 0, "y": 0, "transform": 0, "enabled": True},
        {"name": "DP-2", "mode": "1920x1080@144.00Hz", "scale": 1.0,
         "x": 3440, "y": 0, "transform": 0, "enabled": True},
    ],
    "power": {"suspend_minutes": 5, "off_minutes": 15},
}


def test_monitors_registra_validos(tmp_path):
    (tmp_path / "monitors.json").write_text(json.dumps(VALID_JSON), encoding="utf-8")
    result = run_spec(tmp_path, "valid")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_monitors_disabled(tmp_path):
    data = {"monitors": [{"name": "DP-1", "mode": "preferred", "scale": 1.0,
                           "x": 0, "y": 0, "transform": 0, "enabled": False}],
            "power": {}}
    (tmp_path / "monitors.json").write_text(json.dumps(data), encoding="utf-8")
    result = run_spec(tmp_path, "disabled")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_monitors_transform(tmp_path):
    data = {"monitors": [{"name": "DP-2", "mode": "1920x1080@144.00Hz", "scale": 1.0,
                           "x": 3440, "y": 0, "transform": 1, "enabled": True}],
            "power": {}}
    (tmp_path / "monitors.json").write_text(json.dumps(data), encoding="utf-8")
    result = run_spec(tmp_path, "transform")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_monitors_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_monitors_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "monitors.json").write_text("{corrupto", encoding="utf-8")
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
