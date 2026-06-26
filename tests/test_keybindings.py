import pytest

from ajustes.core.errors import InvalidBindError
from ajustes.core.keybindings import (
    Bind,
    BindAction,
    CatalogBind,
    DISPATCHERS_BY_NAME,
    KeybindingsSettings,
    combo_label,
    detect_conflict,
    mods_from_modmask,
    normalize_key,
    normalize_mods,
    parse_catalog,
    system_catalog,
    validate_bind,
)


def test_normalize_mods_ordena_canonicamente_y_deduplica():
    assert normalize_mods(["shift", "SUPER", "ctrl", "SHIFT"]) == ("SUPER", "CTRL", "SHIFT")
    assert normalize_mods([]) == ()


def test_normalize_key_mayusculas_sin_espacios():
    assert normalize_key(" b ") == "B"
    assert normalize_key("XF86AudioMute") == "XF86AUDIOMUTE"


def test_mods_from_modmask_traduce_bits():
    assert mods_from_modmask(64) == ("SUPER",)
    assert mods_from_modmask(72) == ("SUPER", "ALT")     # 64 + 8
    assert mods_from_modmask(65) == ("SUPER", "SHIFT")   # 64 + 1
    assert mods_from_modmask(0) == ()


def test_combo_de_bind_es_igual_con_mods_desordenados_y_key_en_otra_caja():
    a = Bind(id="k1", mods=("SHIFT", "SUPER"), key="b",
             action=BindAction(type="exec", command="firefox"))
    b = Bind(id="k2", mods=("SUPER", "SHIFT"), key="B",
             action=BindAction(type="exec", command="otro"))
    assert a.combo == b.combo


def test_bind_roundtrip_dict():
    bind = Bind(id="k1", mods=("SUPER", "SHIFT"), key="B",
                action=BindAction(type="exec", command="firefox"),
                description="Abrir Firefox", enabled=True)
    assert Bind.from_dict(bind.to_dict()) == bind


def test_action_dispatcher_roundtrip_y_forma_del_json():
    action = BindAction(type="dispatcher", name="goto_workspace", arg="3")
    data = action.to_dict()
    assert data == {"type": "dispatcher", "name": "goto_workspace", "arg": "3"}
    assert BindAction.from_dict(data) == action
    assert BindAction(type="exec", command="ls").to_dict() == {"type": "exec", "command": "ls"}


def test_settings_roundtrip_ignora_entradas_no_dict_y_acepta_none():
    raw = {"binds": [
        {"id": "k1", "mods": ["SUPER"], "key": "B",
         "action": {"type": "exec", "command": "firefox"},
         "description": "", "enabled": True},
        "basura",
    ]}
    settings = KeybindingsSettings.from_dict(raw)
    assert len(settings.binds) == 1
    assert settings.binds[0].id == "k1"
    assert KeybindingsSettings.from_dict(None) == KeybindingsSettings()


def test_settings_from_dict_tolera_campos_null():
    raw = {"binds": [
        {"id": "k1", "mods": None, "key": "B",
         "action": {"type": "exec", "command": "firefox"}},
        {"id": "k2", "mods": ["SUPER"], "key": "C", "action": None},
        {"id": "k3", "mods": ["SUPER"], "key": "D",
         "action": {"type": "exec", "command": "ls"}},
    ]}
    settings = KeybindingsSettings.from_dict(raw)
    assert [bind.id for bind in settings.binds] == ["k3"]


def test_settings_upsert_remove_y_enabled_son_inmutables():
    bind = Bind(id="k1", mods=("SUPER",), key="B",
                action=BindAction(type="exec", command="firefox"))
    base = KeybindingsSettings()
    added = base.upsert(bind)
    assert base.binds == () and len(added.binds) == 1
    edited = added.upsert(Bind(id="k1", mods=("SUPER",), key="C",
                               action=BindAction(type="exec", command="firefox")))
    assert len(edited.binds) == 1 and edited.binds[0].key == "C"
    assert added.with_enabled("k1", False).binds[0].enabled is False
    assert added.remove("k1").binds == ()


def test_next_id_incrementa_sobre_el_maximo():
    assert KeybindingsSettings().next_id() == "k1"
    settings = KeybindingsSettings(binds=(
        Bind(id="k2", mods=("SUPER",), key="A", action=BindAction(type="exec", command="x")),
        Bind(id="k7", mods=("SUPER",), key="B", action=BindAction(type="exec", command="y")),
    ))
    assert settings.next_id() == "k8"


def test_combo_label_renderiza_legible():
    assert combo_label(("SHIFT", "SUPER"), "B") == "Super + Shift + B"
    assert combo_label(("SUPER",), "XF86AudioMute") == "Super + XF86AudioMute"


# Subconjunto representativo de la salida real: binds Lua (__lua, arg opaco),
# un exec clásico, uno con descripción, un mouse bind y un submap (se filtran).
HYPRCTL_BINDS_FIXTURE = [
    {"locked": False, "mouse": False, "release": False, "repeat": False,
     "modmask": 64, "submap": "", "key": "SPACE", "keycode": 0,
     "description": "", "dispatcher": "__lua", "arg": "7"},
    {"locked": False, "mouse": False, "release": False, "repeat": False,
     "modmask": 72, "submap": "", "key": "Q", "keycode": 0,
     "description": "", "dispatcher": "__lua", "arg": "15"},
    {"locked": False, "mouse": False, "release": False, "repeat": False,
     "modmask": 64, "submap": "", "key": "T", "keycode": 0,
     "description": "Terminal", "dispatcher": "exec", "arg": "alacritty"},
    {"locked": False, "mouse": True, "release": False, "repeat": False,
     "modmask": 64, "submap": "", "key": "mouse:272", "keycode": 0,
     "description": "", "dispatcher": "__lua", "arg": "21"},
    {"locked": False, "mouse": False, "release": False, "repeat": False,
     "modmask": 64, "submap": "resize", "key": "R", "keycode": 0,
     "description": "", "dispatcher": "__lua", "arg": "23"},
    "basura no-dict",
]


def test_parse_catalog_traduce_modmask_y_filtra_mouse_submap_y_basura():
    catalog = parse_catalog(HYPRCTL_BINDS_FIXTURE)
    assert [entry.key for entry in catalog] == ["SPACE", "Q", "T"]
    assert catalog[0].mods == ("SUPER",)
    assert catalog[1].mods == ("SUPER", "ALT")
    assert catalog[0].is_lua and not catalog[2].is_lua
    assert catalog[2].dispatcher == "exec" and catalog[2].arg == "alacritty"
    assert catalog[2].description == "Terminal"


def test_system_catalog_excluye_los_combos_propios():
    catalog = parse_catalog(HYPRCTL_BINDS_FIXTURE)
    # k1 reproduce SUPER+SPACE: su fantasma __lua del catálogo no es "del sistema"
    settings = KeybindingsSettings(binds=(
        Bind(id="k1", mods=("SUPER",), key="space",
             action=BindAction(type="exec", command="wofi --show drun")),
    ))
    assert [entry.key for entry in system_catalog(catalog, settings)] == ["Q", "T"]


def _bind(key="B", mods=("SUPER",), action=None, bind_id="k1"):
    return Bind(id=bind_id, mods=mods, key=key,
                action=action or BindAction(type="exec", command="firefox"))


def test_validate_bind_reglas_basicas():
    validate_bind(_bind())  # válido: no lanza
    with pytest.raises(InvalidBindError):
        validate_bind(_bind(mods=()))
    with pytest.raises(InvalidBindError):
        validate_bind(_bind(key="  "))
    with pytest.raises(InvalidBindError):
        validate_bind(_bind(action=BindAction(type="exec", command="   ")))
    with pytest.raises(InvalidBindError):
        validate_bind(_bind(action=BindAction(type="magia")))


def test_validate_bind_dispatchers():
    validate_bind(_bind(action=BindAction(type="dispatcher", name="fullscreen")))
    validate_bind(_bind(action=BindAction(type="dispatcher", name="goto_workspace", arg="3")))
    validate_bind(_bind(action=BindAction(type="dispatcher", name="focus_direction", arg="left")))
    with pytest.raises(InvalidBindError):  # fuera de la lista blanca
        validate_bind(_bind(action=BindAction(type="dispatcher", name="hackear_nasa")))
    with pytest.raises(InvalidBindError):  # workspace fuera de rango
        validate_bind(_bind(action=BindAction(type="dispatcher", name="goto_workspace", arg="11")))
    with pytest.raises(InvalidBindError):  # workspace no numérico
        validate_bind(_bind(action=BindAction(type="dispatcher", name="goto_workspace", arg="x")))
    with pytest.raises(InvalidBindError):  # dirección inválida
        validate_bind(_bind(action=BindAction(type="dispatcher", name="focus_direction", arg="diagonal")))
    with pytest.raises(InvalidBindError):  # arg sobrante en dispatcher sin arg
        validate_bind(_bind(action=BindAction(type="dispatcher", name="fullscreen", arg="1")))


def test_lista_blanca_completa_del_spec():
    assert set(DISPATCHERS_BY_NAME) == {
        "close_window", "fullscreen", "toggle_float", "goto_workspace",
        "move_to_workspace", "focus_direction", "toggle_special",
    }


def test_detect_conflict_contra_json_y_sistema():
    catalog = parse_catalog(HYPRCTL_BINDS_FIXTURE)
    settings = KeybindingsSettings(binds=(_bind(bind_id="k1", key="B"),))

    # choque con otro bind del JSON
    clash = detect_conflict(_bind(bind_id="k2", key="b"), settings, catalog)
    assert isinstance(clash, Bind) and clash.id == "k1"

    # choque con un bind del sistema (SUPER+SPACE del fixture)
    clash = detect_conflict(_bind(bind_id="k2", key="SPACE"), settings, catalog)
    assert isinstance(clash, CatalogBind) and clash.key == "SPACE"

    # sin choque
    assert detect_conflict(_bind(bind_id="k2", key="Z"), settings, catalog) is None


def test_detect_conflict_excluye_el_propio_id_al_editar():
    settings = KeybindingsSettings(binds=(_bind(bind_id="k1", key="B"),))
    catalog = [CatalogBind(mods=("SUPER",), key="B", dispatcher="__lua",
                           arg="3", description="")]  # fantasma del propio k1
    edited = _bind(bind_id="k1", key="B",
                   action=BindAction(type="exec", command="chromium"))
    assert detect_conflict(edited, settings, catalog, exclude_id="k1") is None
