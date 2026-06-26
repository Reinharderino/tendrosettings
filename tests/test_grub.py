from ajustes.core.grub import (
    CATALOG,
    BooleanFlag,
    ChoiceFlag,
    GrubFlags,
    add_custom_flag,
    build_cmdline,
    parse_cmdline,
    read_default_grub_value,
    read_grub_key,
    remove_token,
    replace_cmdline_in_grub,
    set_grub_key,
)

CURRENT = ("quiet loglevel=3 nvidia_drm.modeset=1 nvidia_drm.fbdev=1 pcie_aspm=off "
           "threadirqs mitigations=auto vsyscall=emulate libata.noacpi=1 "
           "usbcore.initial_descriptor_timeout=5")


# --- catálogo ---

def test_catalog_has_known_flags():
    bool_tokens = {f.token for f in CATALOG if isinstance(f, BooleanFlag)}
    choice_keys = {f.key for f in CATALOG if isinstance(f, ChoiceFlag)}
    assert "quiet" in bool_tokens
    assert "nvidia_drm.modeset=1" in bool_tokens
    assert "loglevel" in choice_keys
    assert "mitigations" in choice_keys


def test_some_flags_marked_risky():
    risky = {getattr(f, "token", getattr(f, "key", "")) for f in CATALOG if f.risky}
    assert "mitigations" in risky


# --- parse ---

def test_parse_boolean_choice_and_custom():
    flags = parse_cmdline(CURRENT)
    assert "quiet" in flags.booleans
    assert "nvidia_drm.modeset=1" in flags.booleans
    assert flags.choices["loglevel"] == "3"
    assert flags.choices["mitigations"] == "auto"
    assert flags.choices["pcie_aspm"] == "off"
    # token no catalogado se preserva como custom
    assert "usbcore.initial_descriptor_timeout=5" in flags.custom


def test_parse_empty_string():
    flags = parse_cmdline("")
    assert flags.booleans == frozenset()
    assert flags.choices == {}
    assert flags.custom == ()


def test_parse_choice_with_unknown_value_goes_to_custom():
    flags = parse_cmdline("loglevel=99")
    assert "loglevel" not in flags.choices
    assert "loglevel=99" in flags.custom


def test_parse_collapses_extra_whitespace():
    flags = parse_cmdline("  quiet   threadirqs  ")
    assert flags.booleans == frozenset({"quiet", "threadirqs"})


# --- build ---

def test_build_round_trip_preserves_token_set():
    flags = parse_cmdline(CURRENT)
    rebuilt = build_cmdline(flags)
    assert set(rebuilt.split()) == set(CURRENT.split())


def test_build_is_deterministic_catalog_order():
    flags = parse_cmdline("threadirqs quiet")
    # quiet va antes que threadirqs en el catálogo, sin importar el input
    assert build_cmdline(flags) == "quiet threadirqs"


def test_build_omits_absent_choice_and_custom_appended_last():
    flags = GrubFlags(
        booleans=frozenset({"quiet"}),
        choices={"loglevel": "3"},
        custom=("foo=bar",),
    )
    assert build_cmdline(flags) == "quiet loglevel=3 foo=bar"


def test_build_empty_flags_is_empty_string():
    assert build_cmdline(GrubFlags(frozenset(), {}, ())) == ""


# --- /etc/default/grub ---

GRUB_FILE = """# comentario
GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_CMDLINE_LINUX_DEFAULT='quiet loglevel=3'
GRUB_CMDLINE_LINUX=""
GRUB_DISABLE_OS_PROBER=false
"""


def test_read_default_grub_value():
    assert read_default_grub_value(GRUB_FILE) == "quiet loglevel=3"


def test_read_default_grub_value_absent_returns_none():
    assert read_default_grub_value("GRUB_TIMEOUT=5\n") is None


def test_replace_cmdline_preserves_other_lines():
    out = replace_cmdline_in_grub(GRUB_FILE, "quiet splash mitigations=off")
    assert "GRUB_CMDLINE_LINUX_DEFAULT=\"quiet splash mitigations=off\"" in out
    assert "GRUB_TIMEOUT=5" in out
    assert "GRUB_DISABLE_OS_PROBER=false" in out
    # sólo una línea DEFAULT
    assert out.count("GRUB_CMDLINE_LINUX_DEFAULT=") == 1
    # no toca la línea LINUX="" (sin DEFAULT)
    assert 'GRUB_CMDLINE_LINUX=""' in out


def test_replace_cmdline_when_absent_appends_line():
    out = replace_cmdline_in_grub("GRUB_TIMEOUT=5\n", "quiet")
    assert 'GRUB_CMDLINE_LINUX_DEFAULT="quiet"' in out
    assert "GRUB_TIMEOUT=5" in out


# --- set_grub_key (genérico) ---

def test_set_grub_key_replaces_existing():
    out = set_grub_key(GRUB_FILE, "GRUB_TIMEOUT", "10")
    assert "GRUB_TIMEOUT=10" in out
    assert out.count("GRUB_TIMEOUT=") == 1
    assert "GRUB_DEFAULT=0" in out          # preserva resto


def test_set_grub_key_appends_when_absent():
    out = set_grub_key("GRUB_TIMEOUT=5\n", "GRUB_DISABLE_OS_PROBER", "false")
    assert "GRUB_DISABLE_OS_PROBER=false" in out
    assert "GRUB_TIMEOUT=5" in out


def test_read_grub_key_strips_quotes():
    assert read_grub_key('GRUB_DEFAULT="1>6"\n', "GRUB_DEFAULT") == "1>6"
    assert read_grub_key("GRUB_TIMEOUT=5\n", "GRUB_TIMEOUT") == "5"


def test_read_grub_key_absent_returns_none():
    assert read_grub_key("GRUB_TIMEOUT=5\n", "GRUB_DEFAULT") is None


def test_set_grub_key_does_not_match_substring_keys():
    # GRUB_TIMEOUT no debe afectar a GRUB_TIMEOUT_STYLE
    content = "GRUB_TIMEOUT=5\nGRUB_TIMEOUT_STYLE=menu\n"
    out = set_grub_key(content, "GRUB_TIMEOUT", "0")
    assert "GRUB_TIMEOUT=0" in out
    assert "GRUB_TIMEOUT_STYLE=menu" in out


# --- operaciones para el constructor por chips ---

def test_remove_token_boolean():
    flags = parse_cmdline("quiet threadirqs")
    out = remove_token(flags, "quiet")
    assert "quiet" not in out.booleans
    assert "threadirqs" in out.booleans


def test_remove_token_choice():
    flags = parse_cmdline("loglevel=3 quiet")
    out = remove_token(flags, "loglevel=3")
    assert "loglevel" not in out.choices


def test_remove_token_custom():
    flags = parse_cmdline("quiet foo=bar")
    out = remove_token(flags, "foo=bar")
    assert "foo=bar" not in out.custom


def test_remove_token_unknown_is_noop():
    flags = parse_cmdline("quiet")
    assert remove_token(flags, "nope") == flags


def test_add_custom_flag_routes_known_boolean():
    flags = add_custom_flag(GrubFlags(frozenset(), {}, ()), "quiet")
    assert "quiet" in flags.booleans
    assert flags.custom == ()


def test_add_custom_flag_routes_known_choice():
    flags = add_custom_flag(GrubFlags(frozenset(), {}, ()), "loglevel=3")
    assert flags.choices["loglevel"] == "3"


def test_add_custom_flag_unknown_goes_to_custom():
    flags = add_custom_flag(GrubFlags(frozenset(), {}, ()), "myflag=1")
    assert "myflag=1" in flags.custom


def test_add_custom_flag_no_duplicates():
    flags = parse_cmdline("quiet foo=bar")
    again = add_custom_flag(flags, "foo=bar")
    assert again.custom.count("foo=bar") == 1


def test_add_custom_flag_multiple_tokens_at_once():
    flags = add_custom_flag(GrubFlags(frozenset(), {}, ()), "quiet  splash")
    assert {"quiet", "splash"} <= flags.booleans
