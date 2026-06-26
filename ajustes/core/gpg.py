from dataclasses import dataclass


@dataclass(frozen=True)
class GpgKey:
    keyid: str
    fingerprint: str
    uid: str
    created: int | None
    expires: int | None


def _epoch(value: str) -> int | None:
    return int(value) if value.isdigit() else None


def parse_secret_keys_colons(output: str) -> list[GpgKey]:
    """Parsea `gpg --list-secret-keys --with-colons` (formato de campos por ':').

    Cada registro 'sec' inicia una clave; el 'fpr' siguiente da el fingerprint y
    el primer 'uid' la identidad.
    """
    keys: list[GpgKey] = []
    keyid = created = expires = None
    fingerprint = uid = None

    def flush():
        nonlocal keyid, fingerprint, uid, created, expires
        if keyid is not None:
            keys.append(GpgKey(
                keyid=keyid, fingerprint=fingerprint or "", uid=uid or "",
                created=created, expires=expires,
            ))
        keyid = fingerprint = uid = created = expires = None

    for line in output.splitlines():
        fields = line.split(":")
        record = fields[0]
        if record == "sec":
            flush()
            keyid = fields[4]
            created = _epoch(fields[5]) if len(fields) > 5 else None
            expires = _epoch(fields[6]) if len(fields) > 6 else None
        elif record == "fpr" and keyid is not None and fingerprint is None:
            fingerprint = fields[9] if len(fields) > 9 else ""
        elif record == "uid" and keyid is not None and uid is None:
            uid = fields[9] if len(fields) > 9 else ""
    flush()
    return keys
