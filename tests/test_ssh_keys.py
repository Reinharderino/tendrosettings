from ajustes.core.ssh_keys import (
    SshKey,
    discover_key_paths,
    parse_agent_fingerprints,
    parse_fingerprint,
)


def test_parse_fingerprint():
    out = "256 SHA256:rh/QpdRXZOGyzpH8xN4QKuBHiylM2CFM9eoR8dHPXjQ user@host (ED25519)"
    bits, fp, comment, ktype = parse_fingerprint(out)
    assert bits == 256
    assert fp == "SHA256:rh/QpdRXZOGyzpH8xN4QKuBHiylM2CFM9eoR8dHPXjQ"
    assert comment == "user@host"
    assert ktype == "ED25519"


def test_parse_fingerprint_comment_with_spaces():
    out = "3072 SHA256:abcDEF my laptop key (RSA)"
    bits, fp, comment, ktype = parse_fingerprint(out)
    assert bits == 3072
    assert comment == "my laptop key"
    assert ktype == "RSA"


def test_parse_fingerprint_invalid_returns_none():
    assert parse_fingerprint("garbage") is None
    assert parse_fingerprint("") is None


def test_parse_agent_fingerprints():
    out = ("256 SHA256:AAA k1 (ED25519)\n"
           "3072 SHA256:BBB k2 (RSA)\n")
    assert parse_agent_fingerprints(out) == {"SHA256:AAA", "SHA256:BBB"}


def test_parse_agent_fingerprints_no_identities():
    assert parse_agent_fingerprints("The agent has no identities.") == set()


def test_discover_key_paths_pairs_priv_and_pub(tmp_path):
    (tmp_path / "id_ed25519").write_text("PRIV", encoding="utf-8")
    (tmp_path / "id_ed25519.pub").write_text("ssh-ed25519 AAA c", encoding="utf-8")
    (tmp_path / "id_rsa").write_text("PRIV", encoding="utf-8")
    (tmp_path / "id_rsa.pub").write_text("ssh-rsa BBB c", encoding="utf-8")
    # ruido a ignorar
    (tmp_path / "known_hosts").write_text("x", encoding="utf-8")
    (tmp_path / "config").write_text("x", encoding="utf-8")
    (tmp_path / "orphan.pub").write_text("no priv", encoding="utf-8")

    paths = discover_key_paths(tmp_path)
    names = {p.name for p in paths}
    assert names == {"id_ed25519", "id_rsa"}


def test_discover_key_paths_missing_dir(tmp_path):
    assert discover_key_paths(tmp_path / "nope") == []


def test_ssh_key_loaded_flag():
    key = SshKey(path="/x/id_ed25519", type="ED25519", bits=256,
                 fingerprint="SHA256:AAA", comment="c", loaded=True)
    assert key.loaded is True
