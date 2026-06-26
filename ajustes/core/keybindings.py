from collections.abc import Iterable
from dataclasses import dataclass

from ajustes.core.errors import InvalidBindError

# Orden canónico para normalizar combinaciones. Los 8 bits de modmask de
# `hyprctl binds -j`; el formulario solo ofrece los 4 primeros (FORM_MODS).
CANONICAL_MODS = ("SUPER", "CTRL", "ALT", "SHIFT", "CAPS", "MOD2", "MOD3", "MOD5")
FORM_MODS = ("SUPER", "CTRL", "ALT", "SHIFT")
# El orden de inserción debe coincidir con CANONICAL_MODS: mods_from_modmask
# depende de él para devolver tuplas ya canónicas.
MODMASK_NAMES = {64: "SUPER", 4: "CTRL", 8: "ALT", 1: "SHIFT",
                 2: "CAPS", 16: "MOD2", 32: "MOD3", 128: "MOD5"}
LUA_DISPATCHER = "__lua"  # así reporta hyprctl los binds registrados desde Lua


def normalize_mods(mods: Iterable[str]) -> tuple[str, ...]:
    chosen = {str(mod).upper() for mod in mods}
    return tuple(mod for mod in CANONICAL_MODS if mod in chosen)


def normalize_key(key: str) -> str:
    return str(key).strip().upper()


def mods_from_modmask(modmask: int) -> tuple[str, ...]:
    return tuple(name for bit, name in MODMASK_NAMES.items() if modmask & bit)


def combo_label(mods: Iterable[str], key: str) -> str:
    # La key se muestra tal cual se guardó (Hyprland distingue nombres como
    # "XF86AudioMute"); solo los mods se reescriben con caja de título.
    parts = [mod.capitalize() for mod in normalize_mods(mods)]
    parts.append(str(key).strip())
    return " + ".join(parts)


@dataclass(frozen=True)
class BindAction:
    type: str       # "exec" | "dispatcher"
    command: str = ""  # solo exec
    name: str = ""     # solo dispatcher (lista blanca)
    arg: str = ""      # solo dispatcher, según arg_kind

    @classmethod
    def from_dict(cls, data: dict) -> "BindAction":
        return cls(
            type=str(data.get("type", "")),
            command=str(data.get("command", "")),
            name=str(data.get("name", "")),
            arg=str(data.get("arg", "")),
        )

    def to_dict(self) -> dict:
        if self.type == "exec":
            return {"type": "exec", "command": self.command}
        return {"type": "dispatcher", "name": self.name, "arg": self.arg}


@dataclass(frozen=True)
class Bind:
    id: str
    mods: tuple[str, ...]
    key: str
    action: BindAction
    description: str = ""
    enabled: bool = True

    @property
    def combo(self) -> tuple[tuple[str, ...], str]:
        return (normalize_mods(self.mods), normalize_key(self.key))

    @classmethod
    def from_dict(cls, data: dict) -> "Bind":
        return cls(
            id=str(data.get("id", "")),
            mods=tuple(str(mod) for mod in data.get("mods", [])),
            key=str(data.get("key", "")),
            action=BindAction.from_dict(data.get("action", {})),
            description=str(data.get("description", "")),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mods": list(self.mods),
            "key": self.key,
            "action": self.action.to_dict(),
            "description": self.description,
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class KeybindingsSettings:
    """Inmutable por contrato: construir solo vía from_dict/upsert/remove/with_enabled."""

    binds: tuple[Bind, ...] = ()

    @classmethod
    def from_dict(cls, data: dict | None) -> "KeybindingsSettings":
        if not data:
            return cls()
        binds = []
        for raw in data.get("binds", []):
            if not isinstance(raw, dict):
                continue
            try:
                binds.append(Bind.from_dict(raw))
            except (TypeError, AttributeError, ValueError):
                continue
        return cls(binds=tuple(binds))

    def to_dict(self) -> dict:
        return {"binds": [bind.to_dict() for bind in self.binds]}

    def upsert(self, bind: Bind) -> "KeybindingsSettings":
        if any(existing.id == bind.id for existing in self.binds):
            return KeybindingsSettings(binds=tuple(
                bind if existing.id == bind.id else existing for existing in self.binds
            ))
        return KeybindingsSettings(binds=(*self.binds, bind))

    def remove(self, bind_id: str) -> "KeybindingsSettings":
        return KeybindingsSettings(binds=tuple(
            bind for bind in self.binds if bind.id != bind_id
        ))

    def with_enabled(self, bind_id: str, enabled: bool) -> "KeybindingsSettings":
        return KeybindingsSettings(binds=tuple(
            Bind(id=b.id, mods=b.mods, key=b.key, action=b.action,
                 description=b.description, enabled=enabled) if b.id == bind_id else b
            for b in self.binds
        ))

    def next_id(self) -> str:
        taken = [int(b.id[1:]) for b in self.binds
                 if b.id.startswith("k") and b.id[1:].isdigit()]
        return f"k{max(taken, default=0) + 1}"


@dataclass(frozen=True)
class CatalogBind:
    """Un bind vivo reportado por hyprctl; read-only en la UI."""

    mods: tuple[str, ...]
    key: str
    dispatcher: str
    arg: str
    description: str

    @property
    def is_lua(self) -> bool:
        return self.dispatcher == LUA_DISPATCHER

    @property
    def combo(self) -> tuple[tuple[str, ...], str]:
        return (normalize_mods(self.mods), normalize_key(self.key))


def parse_catalog(raw: list) -> list[CatalogBind]:
    """Traduce la salida de `hyprctl binds -j` al dominio.

    Solo binds de teclado del submap raíz (ratón y submaps están fuera del
    alcance v1). Entradas malformadas se omiten: el catálogo es informativo,
    nunca debe tumbar el módulo.
    """
    catalog = []
    for entry in raw:
        if not isinstance(entry, dict) or entry.get("mouse") or entry.get("submap"):
            continue
        key = str(entry.get("key", ""))
        if not key:
            continue
        try:
            mods = mods_from_modmask(int(entry.get("modmask", 0)))
        except (TypeError, ValueError):
            continue
        catalog.append(CatalogBind(
            mods=mods,
            key=key,
            dispatcher=str(entry.get("dispatcher", "")),
            arg=str(entry.get("arg", "")),
            description=str(entry.get("description", "")),
        ))
    return catalog


def system_catalog(
    catalog: list[CatalogBind], settings: KeybindingsSettings
) -> list[CatalogBind]:
    """Catálogo sin los binds propios: tras `hyprctl reload` los binds del JSON
    también aparecen en hyprctl (como __lua); en la UI viven en "Mis atajos"."""
    owned = {bind.combo for bind in settings.binds}
    return [entry for entry in catalog if entry.combo not in owned]


DIRECTIONS = ("left", "right", "up", "down")
WORKSPACE_MIN, WORKSPACE_MAX = 1, 10


@dataclass(frozen=True)
class DispatcherSpec:
    name: str
    label: str     # etiqueta de la UI, en español
    arg_kind: str  # "none" | "workspace" | "direction"


# Lista blanca compartida con lua/settings/init.lua (mantener en sintonía).
DISPATCHERS = (
    DispatcherSpec("close_window", "Cerrar ventana", "none"),
    DispatcherSpec("fullscreen", "Pantalla completa", "none"),
    DispatcherSpec("toggle_float", "Alternar flotante", "none"),
    DispatcherSpec("goto_workspace", "Ir al workspace", "workspace"),
    DispatcherSpec("move_to_workspace", "Mover ventana al workspace", "workspace"),
    DispatcherSpec("focus_direction", "Mover el foco", "direction"),
    DispatcherSpec("toggle_special", "Workspace especial", "none"),
)
DISPATCHERS_BY_NAME = {spec.name: spec for spec in DISPATCHERS}


def validate_bind(bind: Bind) -> None:
    if not normalize_mods(bind.mods):
        raise InvalidBindError("elige al menos un modificador")
    if not normalize_key(bind.key):
        raise InvalidBindError("elige una tecla")
    action = bind.action
    if action.type == "exec":
        if not action.command.strip():
            raise InvalidBindError("el comando no puede estar vacío")
        return
    if action.type != "dispatcher":
        raise InvalidBindError(f"tipo de acción desconocido: {action.type!r}")
    spec = DISPATCHERS_BY_NAME.get(action.name)
    if spec is None:
        raise InvalidBindError(f"acción fuera de la lista blanca: {action.name!r}")
    if spec.arg_kind == "none" and action.arg:
        raise InvalidBindError(f"{spec.label} no lleva argumento")
    if spec.arg_kind == "workspace":
        if not action.arg.isdigit() or not WORKSPACE_MIN <= int(action.arg) <= WORKSPACE_MAX:
            raise InvalidBindError(
                f"workspace debe ser un número {WORKSPACE_MIN}-{WORKSPACE_MAX}"
            )
    if spec.arg_kind == "direction" and action.arg not in DIRECTIONS:
        raise InvalidBindError(f"dirección inválida: {action.arg!r}")


def detect_conflict(
    candidate: Bind,
    settings: KeybindingsSettings,
    catalog: list[CatalogBind],
    exclude_id: str | None = None,
) -> Bind | CatalogBind | None:
    """Devuelve el bind con el que choca la combinación, o None.

    Los combos del JSON se excluyen del catálogo del sistema: tras un reload
    los binds propios también aparecen en hyprctl y serían falsos positivos.
    """
    combo = candidate.combo
    for bind in settings.binds:
        if bind.id != exclude_id and bind.combo == combo:
            return bind
    owned = {bind.combo for bind in settings.binds}
    for entry in catalog:
        if entry.combo == combo and entry.combo not in owned:
            return entry
    return None
