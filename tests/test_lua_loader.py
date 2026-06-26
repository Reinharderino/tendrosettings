import json
import os
import pathlib
import shutil
import subprocess

import pytest

LUA = shutil.which("lua")
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.mark.skipif(LUA is None, reason="no hay intérprete lua en el sistema")
def test_loader_lua(tmp_path):
    (tmp_path / "valido.json").write_text(
        json.dumps(
            {
                "gaps": 12,
                "nombre": "tendró ñ",
                "lista": [1, 2, 3],
                "anidado": {"x": -1.5},
                "nulo": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "corrupto.json").write_text("{rotísimo", encoding="utf-8")
    (tmp_path / "raiz_lista.json").write_text("[1, 2]", encoding="utf-8")

    result = subprocess.run(
        [LUA, "tests/lua/loader_spec.lua"],
        env={**os.environ, "HYPR_AJUSTES_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


@pytest.mark.skipif(LUA is None, reason="no hay intérprete lua en el sistema")
def test_loader_no_crashea_sin_home():
    env = {k: v for k, v in os.environ.items() if k not in ("HOME", "HYPR_AJUSTES_DIR")}

    result = subprocess.run(
        [
            LUA,
            "-e",
            'package.path = "lua/?/init.lua;" .. package.path\n'
            'local s = require("settings")\n'
            'local d = s.load("lo_que_sea", { ok = true })\n'
            "assert(d.ok == true)\n"
            'print("OK")',
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
