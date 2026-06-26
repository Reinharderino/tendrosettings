import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Snapshot:
    num: int
    type: str
    date: str
    description: str
    cleanup: str
    pre_num: int | None


def _text(root: ET.Element, tag: str, default: str = "") -> str:
    el = root.find(tag)
    return el.text if (el is not None and el.text is not None) else default


def parse_info_xml(content: str) -> Snapshot | None:
    """Parsea un info.xml de snapper. Devuelve None si es inválido o sin num."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None

    num_text = _text(root, "num")
    if not num_text.isdigit():
        return None

    pre_text = _text(root, "pre_num")
    return Snapshot(
        num=int(num_text),
        type=_text(root, "type", "single"),
        date=_text(root, "date"),
        description=_text(root, "description"),
        cleanup=_text(root, "cleanup"),
        pre_num=int(pre_text) if pre_text.isdigit() else None,
    )


def read_snapshots(snapshots_dir: Path) -> list[Snapshot]:
    """Lee /.snapshots/<N>/info.xml (sin privilegios) y devuelve los snapshots
    ordenados por número descendente. Directorios sin info.xml válido se ignoran."""
    if not snapshots_dir.is_dir():
        return []
    result: list[Snapshot] = []
    for entry in snapshots_dir.iterdir():
        if not (entry.is_dir() and entry.name.isdigit()):
            continue
        info = entry / "info.xml"
        if not info.is_file():
            continue
        try:
            snapshot = parse_info_xml(info.read_text(encoding="utf-8"))
        except OSError:
            continue
        if snapshot is not None:
            result.append(snapshot)
    return sorted(result, key=lambda s: s.num, reverse=True)
