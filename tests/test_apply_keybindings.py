import json
from dataclasses import dataclass

import pytest

from ajustes.core.apply_keybindings import ApplyKeybindings
from ajustes.core.config_store import ConfigStore
from ajustes.core.errors import BindConflictError, InvalidBindError
from ajustes.core.keybindings import (
    Bind,
    BindAction,
    CatalogBind,
    KeybindingsSettings,
)


@dataclass
class FakeBridge:
    available: bool = True
    reloads: int = 0

    def is_available(self) -> bool:
        return self.available

    def reload(self) -> None:
        self.reloads += 1


def make_apply(tmp_path, available=True):
    bridge = FakeBridge(available=available)
    return ApplyKeybindings(store=ConfigStore(settings_dir=tmp_path), bridge=bridge), bridge


def _bind(key="B", bind_id="k1", command="firefox"):
    return Bind(id=bind_id, mods=("SUPER",), key=key,
                action=BindAction(type="exec", command=command))


def test_save_escribe_json_y_recarga(tmp_path):
    apply_kb, bridge = make_apply(tmp_path)

    result = apply_kb.save(KeybindingsSettings(), _bind(), catalog=[])

    data = json.loads((tmp_path / "keybindings.json").read_text(encoding="utf-8"))
    assert data["binds"][0]["id"] == "k1"
    assert result.applied_live and bridge.reloads == 1
    assert len(result.settings.binds) == 1


def test_save_sin_sesion_no_recarga(tmp_path):
    apply_kb, bridge = make_apply(tmp_path, available=False)

    result = apply_kb.save(KeybindingsSettings(), _bind(), catalog=[])

    assert not result.applied_live and bridge.reloads == 0


def test_save_con_conflicto_no_escribe_nada(tmp_path):
    apply_kb, _ = make_apply(tmp_path)
    catalog = [CatalogBind(mods=("SUPER",), key="B", dispatcher="exec",
                           arg="alacritty", description="")]

    with pytest.raises(BindConflictError) as exc_info:
        apply_kb.save(KeybindingsSettings(), _bind(), catalog=catalog)

    assert exc_info.value.conflicting.key == "B"
    assert not (tmp_path / "keybindings.json").exists()


def test_save_invalido_no_escribe_nada(tmp_path):
    apply_kb, _ = make_apply(tmp_path)

    with pytest.raises(InvalidBindError):
        apply_kb.save(KeybindingsSettings(), _bind(command="  "), catalog=[])

    assert not (tmp_path / "keybindings.json").exists()


def test_editar_el_mismo_bind_no_choca_consigo_mismo(tmp_path):
    apply_kb, _ = make_apply(tmp_path)
    settings = KeybindingsSettings(binds=(_bind(),))
    edited = _bind(command="chromium")

    result = apply_kb.save(settings, edited, catalog=[])

    assert result.settings.binds[0].action.command == "chromium"


def test_delete_y_set_enabled_persisten(tmp_path):
    apply_kb, bridge = make_apply(tmp_path)
    settings = apply_kb.save(KeybindingsSettings(), _bind(), catalog=[]).settings

    disabled = apply_kb.set_enabled(settings, "k1", False).settings
    assert disabled.binds[0].enabled is False

    removed = apply_kb.delete(disabled, "k1").settings
    assert removed.binds == ()
    data = json.loads((tmp_path / "keybindings.json").read_text(encoding="utf-8"))
    assert data == {"binds": []}
    assert bridge.reloads == 3
