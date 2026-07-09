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
        [LUA, "tests/lua/autostart_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def test_autostart_lanza_enabled(tmp_path):
    data = {"entries": [
        {"command": "vesktop", "enabled": True},
        {"command": "telegram", "enabled": True},
    ]}
    (tmp_path / "autostart.json").write_text(json.dumps(data), encoding="utf-8")
    result = run_spec(tmp_path, "valid")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_autostart_salta_disabled(tmp_path):
    data = {"entries": [
        {"command": "vesktop", "enabled": True},
        {"command": "telegram", "enabled": False},
    ]}
    (tmp_path / "autostart.json").write_text(json.dumps(data), encoding="utf-8")
    result = run_spec(tmp_path, "skip_disabled")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_autostart_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_autostart_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "autostart.json").write_text("{corrupto", encoding="utf-8")
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
