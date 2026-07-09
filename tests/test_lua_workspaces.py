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
        [LUA, "tests/lua/workspaces_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def test_workspaces_registra_validos(tmp_path):
    data = {"workspaces": [
        {"number": 1, "monitor": "DP-1", "persistent": True},
        {"number": 2, "monitor": "DP-2", "persistent": False},
    ]}
    (tmp_path / "workspaces.json").write_text(json.dumps(data), encoding="utf-8")
    result = run_spec(tmp_path, "valid")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_workspaces_omite_sin_monitor(tmp_path):
    data = {"workspaces": [{"number": 3, "monitor": "", "persistent": True}]}
    (tmp_path / "workspaces.json").write_text(json.dumps(data), encoding="utf-8")
    result = run_spec(tmp_path, "skip_no_monitor")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_workspaces_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_workspaces_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "workspaces.json").write_text("{corrupto", encoding="utf-8")
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
