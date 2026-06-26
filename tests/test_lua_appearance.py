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
        [LUA, "tests/lua/appearance_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path), "SPEC_CASE": case},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


VALID_JSON = {
    "gaps_in": 8, "gaps_out": 16, "border_size": 3,
    "rounding": 20, "blur_enabled": False, "blur_size": 5, "blur_passes": 2,
    "animations_enabled": False,
    "active_color_1": "rgba(112233ff)", "active_color_2": "rgba(445566ff)",
    "gradient_angle": 90, "inactive_color": "rgba(778899aa)",
}


def test_appearance_aplica_valores(tmp_path):
    (tmp_path / "appearance.json").write_text(json.dumps(VALID_JSON), encoding="utf-8")
    result = run_spec(tmp_path, "valid")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_appearance_json_ausente_no_lanza(tmp_path):
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_appearance_json_corrupto_no_lanza(tmp_path):
    (tmp_path / "appearance.json").write_text("{corrupto", encoding="utf-8")
    result = run_spec(tmp_path, "empty")
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
