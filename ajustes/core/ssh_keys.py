import re
from dataclasses import dataclass
from pathlib import Path

# Línea de ssh-keygen -lf / ssh-add -l:  "256 SHA256:xxxx comentario con espacios (ED25519)"
_FP_RE = re.compile(r"^(\d+)\s+(SHA256:\S+|MD5:\S+)\s+(.*?)\s+\(([A-Z0-9-]+)\)\s*$")

# Ficheros de ~/.ssh que NO son claves.
_NOT_KEYS = {"known_hosts", "known_hosts.old", "config", "authorized_keys", "agent"}


@dataclass(frozen=True)
class SshKey:
    path: str
    type: str
    bits: int
    fingerprint: str
    comment: str
    loaded: bool


def parse_fingerprint(line: str) -> tuple[int, str, str, str] | None:
    """Parsea una línea de ssh-keygen -lf → (bits, fingerprint, comentario, tipo)."""
    match = _FP_RE.match(line.strip())
    if not match:
        return None
    return int(match.group(1)), match.group(2), match.group(3).strip(), match.group(4)


def parse_agent_fingerprints(output: str) -> set[str]:
    """Fingerprints cargados en el agente, desde `ssh-add -l`."""
    fingerprints: set[str] = set()
    for line in output.splitlines():
        parsed = parse_fingerprint(line)
        if parsed:
            fingerprints.add(parsed[1])
    return fingerprints


def discover_key_paths(ssh_dir: Path) -> list[Path]:
    """Claves privadas en ~/.ssh: ficheros con un `.pub` hermano (y no conocidos como no-clave)."""
    if not ssh_dir.is_dir():
        return []
    keys: list[Path] = []
    for entry in sorted(ssh_dir.iterdir()):
        if entry.suffix == ".pub" or entry.name in _NOT_KEYS or not entry.is_file():
            continue
        if (ssh_dir / f"{entry.name}.pub").is_file():
            keys.append(entry)
    return keys
