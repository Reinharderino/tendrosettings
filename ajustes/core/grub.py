import re
from dataclasses import dataclass

# Categorías para agrupar en la UI.
BOOT = "Arranque"
PERF = "Rendimiento"
POWER = "Energía"
GPU = "GPU NVIDIA"
STORAGE = "Almacenamiento"
SECURITY = "Seguridad"
COMPAT = "Compatibilidad"


@dataclass(frozen=True)
class BooleanFlag:
    token: str          # token completo: "quiet" o "nvidia_drm.modeset=1"
    label: str
    description: str
    category: str
    risky: bool = False


@dataclass(frozen=True)
class ChoiceFlag:
    key: str            # clave antes del '=': "loglevel"
    label: str
    description: str
    category: str
    values: tuple[str, ...]
    risky: bool = False


# Catálogo ordenado de tweaks típicos. El orden define el orden del cmdline generado.
CATALOG: tuple = (
    BooleanFlag("quiet", "quiet", "Arranque silencioso (oculta mensajes del kernel)", BOOT),
    BooleanFlag("splash", "splash", "Muestra la pantalla de bienvenida (plymouth)", BOOT),
    ChoiceFlag("loglevel", "loglevel", "Nivel de detalle de logs del kernel (0–7)", BOOT,
               ("0", "1", "2", "3", "4", "5", "6", "7")),
    ChoiceFlag("mitigations", "mitigations",
               "Mitigaciones de vulnerabilidades de CPU. 'off' = más rápido, menos seguro",
               PERF, ("auto", "auto,nosmt", "off"), risky=True),
    BooleanFlag("nowatchdog", "nowatchdog", "Desactiva watchdogs de hardware (menos latencia)", PERF),
    BooleanFlag("nmi_watchdog=0", "nmi_watchdog=0", "Desactiva el NMI watchdog", PERF),
    BooleanFlag("threadirqs", "threadirqs", "IRQs en hilos (mejor para audio/tiempo real)", PERF),
    ChoiceFlag("transparent_hugepage", "transparent_hugepage",
               "Páginas enormes transparentes", PERF, ("always", "madvise", "never")),
    BooleanFlag("zswap.enabled=0", "zswap.enabled=0", "Desactiva zswap", PERF),
    ChoiceFlag("pcie_aspm", "pcie_aspm", "Gestión de energía de PCIe", POWER,
               ("default", "performance", "powersave", "powersupersave", "off")),
    ChoiceFlag("intel_pstate", "intel_pstate", "Driver de frecuencia de CPU Intel", POWER,
               ("active", "passive", "disable")),
    BooleanFlag("nvidia_drm.modeset=1", "nvidia_drm.modeset=1", "KMS de NVIDIA (necesario en Wayland)", GPU),
    BooleanFlag("nvidia_drm.fbdev=1", "nvidia_drm.fbdev=1", "Framebuffer de NVIDIA vía DRM", GPU),
    BooleanFlag("libata.noacpi=1", "libata.noacpi=1", "Ignora ACPI en SATA (evita ciertos cuelgues)", STORAGE),
    BooleanFlag("nvme.noacpi=1", "nvme.noacpi=1", "Ignora ACPI en NVMe (ahorro/estabilidad)", STORAGE),
    BooleanFlag("sysrq_always_enabled=1", "sysrq_always_enabled=1", "Habilita todas las funciones SysRq", SECURITY),
    ChoiceFlag("vsyscall", "vsyscall", "Compatibilidad de vsyscall para binarios antiguos", COMPAT,
               ("emulate", "xonly", "none")),
)

_BOOLEAN_TOKENS = {f.token for f in CATALOG if isinstance(f, BooleanFlag)}
_CHOICES = {f.key: f for f in CATALOG if isinstance(f, ChoiceFlag)}


@dataclass(frozen=True)
class GrubFlags:
    booleans: frozenset[str]    # tokens booleanos activos
    choices: dict[str, str]     # key -> valor seleccionado (sólo presentes)
    custom: tuple[str, ...]     # tokens no catalogados, en orden original


def parse_cmdline(raw: str) -> GrubFlags:
    """Parsea un cmdline en GrubFlags, preservando lo no catalogado como custom."""
    booleans: set[str] = set()
    choices: dict[str, str] = {}
    custom: list[str] = []
    for token in raw.split():
        if token in _BOOLEAN_TOKENS:
            booleans.add(token)
            continue
        if "=" in token:
            key, value = token.split("=", 1)
            spec = _CHOICES.get(key)
            if spec is not None and value in spec.values:
                choices[key] = value
                continue
        if token not in custom:
            custom.append(token)
    return GrubFlags(frozenset(booleans), choices, tuple(custom))


def build_cmdline(flags: GrubFlags) -> str:
    """Reconstruye el cmdline en orden de catálogo; los custom van al final."""
    tokens: list[str] = []
    for spec in CATALOG:
        if isinstance(spec, BooleanFlag):
            if spec.token in flags.booleans:
                tokens.append(spec.token)
        elif spec.key in flags.choices:
            tokens.append(f"{spec.key}={flags.choices[spec.key]}")
    tokens.extend(flags.custom)
    return " ".join(tokens)


def remove_token(flags: GrubFlags, token: str) -> GrubFlags:
    """Quita un token activo (booleano, choice key=value o custom). Si no está, no cambia."""
    if token in flags.booleans:
        return GrubFlags(flags.booleans - {token}, flags.choices, flags.custom)
    if "=" in token:
        key, value = token.split("=", 1)
        if flags.choices.get(key) == value:
            rest = {k: v for k, v in flags.choices.items() if k != key}
            return GrubFlags(flags.booleans, rest, flags.custom)
    if token in flags.custom:
        return GrubFlags(flags.booleans, flags.choices,
                         tuple(t for t in flags.custom if t != token))
    return flags


def add_custom_flag(flags: GrubFlags, raw: str) -> GrubFlags:
    """Añade uno o más tokens (texto libre), enrutándolos por el catálogo y sin
    duplicar. 'quiet' activa el booleano; 'loglevel=3' fija el choice; el resto va a custom."""
    return parse_cmdline(build_cmdline(flags) + " " + raw)


_DEFAULT_LINE = re.compile(r'^GRUB_CMDLINE_LINUX_DEFAULT=.*$', re.MULTILINE)


def read_grub_key(content: str, key: str) -> str | None:
    """Devuelve el valor de `KEY=...` (sin comillas), o None si no existe."""
    match = re.search(rf"^{re.escape(key)}=(.*)$", content, re.MULTILINE)
    if match is None:
        return None
    rhs = match.group(1).strip()
    if len(rhs) >= 2 and rhs[0] in "\"'" and rhs[-1] == rhs[0]:
        rhs = rhs[1:-1]
    return rhs


def read_default_grub_value(content: str) -> str | None:
    """Extrae el valor de GRUB_CMDLINE_LINUX_DEFAULT (sin comillas), o None."""
    return read_grub_key(content, "GRUB_CMDLINE_LINUX_DEFAULT")


def set_grub_key(content: str, key: str, rhs: str) -> str:
    """Reemplaza la línea `KEY=...` preservando el resto; la añade si no existe.
    `rhs` es el lado derecho literal (el llamador decide comillas)."""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    new_line = f"{key}={rhs}"
    if pattern.search(content):
        return pattern.sub(lambda _m: new_line, content, count=1)
    suffix = "" if content.endswith("\n") or content == "" else "\n"
    return content + suffix + new_line + "\n"


def replace_cmdline_in_grub(content: str, new_value: str) -> str:
    """Reemplaza sólo GRUB_CMDLINE_LINUX_DEFAULT (entre comillas dobles)."""
    return set_grub_key(content, "GRUB_CMDLINE_LINUX_DEFAULT", f'"{new_value}"')
