from ajustes.core.gpg import GpgKey, parse_secret_keys_colons

COLONS = (
    "sec:u:255:22:ABCDEF1234567890:1700000000:1800000000::u:::scESC:::+::ed25519:::0:\n"
    "fpr:::::::::AAAA1111BBBB2222CCCC3333DDDD4444EEEE5555:\n"
    "grp:::::::::0000:\n"
    "uid:u::::1700000000::HASH::Nombre Apellido <mail@x.com>::::::::::0:\n"
    "ssb:u:255:18:1111222233334444:1700000000::::::e:::+::cv25519::\n"
)


def test_parse_single_key():
    keys = parse_secret_keys_colons(COLONS)
    assert len(keys) == 1
    k = keys[0]
    assert k.keyid == "ABCDEF1234567890"
    assert k.fingerprint == "AAAA1111BBBB2222CCCC3333DDDD4444EEEE5555"
    assert k.uid == "Nombre Apellido <mail@x.com>"
    assert k.created == 1700000000
    assert k.expires == 1800000000


def test_parse_no_expiry():
    text = (
        "sec:u:255:22:KEYNOEXP:1700000000::::u:::scESC:::+::ed25519:::0:\n"
        "fpr:::::::::FFFF:\n"
        "uid:u::::1700000000::H::Solo Uid::::::::::0:\n"
    )
    assert parse_secret_keys_colons(text)[0].expires is None


def test_parse_multiple_keys():
    text = COLONS + (
        "sec:u:255:22:SECONDKEY0000000:1600000000:1700000000::u:::scESC:::+::ed25519:::0:\n"
        "fpr:::::::::BBBB:\n"
        "uid:u::::1600000000::H2::Otro <o@x.com>::::::::::0:\n"
    )
    keys = parse_secret_keys_colons(text)
    assert [k.keyid for k in keys] == ["ABCDEF1234567890", "SECONDKEY0000000"]


def test_parse_empty():
    assert parse_secret_keys_colons("") == []


def test_gpgkey_dataclass():
    k = GpgKey(keyid="X", fingerprint="F", uid="u", created=1, expires=None)
    assert k.expires is None
