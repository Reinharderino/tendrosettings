from dataclasses import dataclass


@dataclass(frozen=True)
class CaCert:
    label: str
    trust: str
    category: str
    uri: str


def parse_trust_list(output: str) -> list[CaCert]:
    """Parsea `trust list` (p11-kit): bloques `pkcs11:...` + líneas `clave: valor`.
    Sólo devuelve certificados con etiqueta."""
    certs: list[CaCert] = []
    uri = None
    fields: dict[str, str] = {}

    def flush():
        nonlocal uri, fields
        if uri is not None and fields.get("label"):
            certs.append(CaCert(
                label=fields.get("label", ""),
                trust=fields.get("trust", ""),
                category=fields.get("category", ""),
                uri=uri,
            ))
        uri, fields = None, {}

    for line in output.splitlines():
        if line.startswith("pkcs11:"):
            flush()
            uri = line.strip()
        elif uri is not None and ":" in line and line[:1] in (" ", "\t"):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    flush()
    return certs
