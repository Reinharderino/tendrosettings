import re
from dataclasses import dataclass

# Boot0001* Etiqueta\tHD(...)...   ('*' = activa; sin '*' = inactiva)
_ENTRY_RE = re.compile(r"^Boot([0-9A-Fa-f]{4})(\*?)\s+(.*)$")


@dataclass(frozen=True)
class BootEntry:
    num: str            # id hex de 4 dígitos, p.ej. "0001"
    label: str
    active: bool
    is_current: bool


@dataclass(frozen=True)
class EfiBootState:
    entries: tuple[BootEntry, ...]
    order: tuple[str, ...]      # nums en orden de arranque
    current: str | None         # BootCurrent
    boot_next: str | None       # BootNext (arranque único), si está
    timeout: int                # Timeout del firmware (segundos)


def parse_efibootmgr(text: str) -> EfiBootState:
    """Parsea la salida de `efibootmgr`. Tolerante a campos ausentes."""
    current = boot_next = None
    order: tuple[str, ...] = ()
    timeout = 0
    raw_entries: list[tuple[str, bool, str]] = []

    for line in text.splitlines():
        if line.startswith("BootCurrent:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("BootNext:"):
            boot_next = line.split(":", 1)[1].strip()
        elif line.startswith("BootOrder:"):
            order = tuple(n.strip() for n in line.split(":", 1)[1].split(",") if n.strip())
        elif line.startswith("Timeout:"):
            digits = re.search(r"\d+", line)
            timeout = int(digits.group(0)) if digits else 0
        else:
            match = _ENTRY_RE.match(line)
            if match:
                num, star, rest = match.group(1), match.group(2), match.group(3)
                label = rest.split("\t", 1)[0].strip()
                raw_entries.append((num, star == "*", label))

    entries = tuple(
        BootEntry(num=num, label=label, active=active, is_current=(num == current))
        for num, active, label in raw_entries
    )
    return EfiBootState(
        entries=entries, order=order, current=current,
        boot_next=boot_next, timeout=timeout,
    )


def build_bootorder(state: EfiBootState, first_num: str) -> list[str]:
    """Nuevo BootOrder con `first_num` al frente, preservando el resto del orden."""
    rest = [n for n in state.order if n != first_num]
    return [first_num, *rest]
