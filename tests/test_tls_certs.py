from ajustes.core.tls_certs import CaCert, parse_trust_list

SAMPLE = """pkcs11:id=%ab%cd;type=cert
    type: certificate
    label: Some Root CA
    trust: anchor
    category: authority

pkcs11:id=%ef;type=cert
    type: certificate
    label: Another CA R3
    trust: anchor
    category: authority
"""


def test_parse_two_certs():
    certs = parse_trust_list(SAMPLE)
    assert len(certs) == 2
    assert certs[0] == CaCert(
        label="Some Root CA", trust="anchor", category="authority",
        uri="pkcs11:id=%ab%cd;type=cert",
    )
    assert certs[1].label == "Another CA R3"


def test_parse_skips_blocks_without_label():
    text = "pkcs11:id=%x;type=cert\n    type: certificate\n    trust: anchor\n"
    assert parse_trust_list(text) == []


def test_parse_empty():
    assert parse_trust_list("") == []
