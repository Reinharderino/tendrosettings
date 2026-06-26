from dataclasses import dataclass

# Curvas bezier disponibles para asignar a una animación. "default" y "linear"
# son built-in de Hyprland; "myBezier" la define hyprland.lua. Editar/crear curvas
# nuevas queda fuera del alcance (necesitaría un editor de puntos de control).
BEZIER_CHOICES: tuple[str, ...] = ("default", "linear", "myBezier")

_SPEED_MIN, _SPEED_MAX = 0.1, 50.0

# Catálogo de animaciones configurables y sus defaults = bloque de hl.animation
# hardcodeado en hyprland.lua (mantener en sintonía). Las no definidas allí toman
# valores razonables. (name, enabled, speed, bezier, style)
_DEFAULTS: tuple[tuple[str, bool, float, str, str], ...] = (
    ("windows",          True, 7.0,  "myBezier", ""),
    ("windowsIn",        True, 7.0,  "myBezier", ""),
    ("windowsOut",       True, 7.0,  "default",  "popin 80%"),
    ("windowsMove",      True, 7.0,  "default",  ""),
    ("layers",           True, 7.0,  "default",  ""),
    ("fade",             True, 7.0,  "default",  ""),
    ("border",           True, 10.0, "default",  ""),
    ("borderangle",      True, 8.0,  "default",  ""),
    ("workspaces",       True, 6.0,  "default",  ""),
    ("specialWorkspace", True, 6.0,  "default",  ""),
)

CONFIGURABLE_LEAVES: tuple[str, ...] = tuple(name for name, *_ in _DEFAULTS)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class AnimationLeaf:
    name: str
    enabled: bool
    speed: float
    bezier: str
    style: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "speed": self.speed,
            "bezier": self.bezier,
            "style": self.style,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnimationLeaf":
        bezier = str(data.get("bezier", "default"))
        if bezier not in BEZIER_CHOICES:
            bezier = "default"
        return cls(
            name=str(data.get("name", "")),
            enabled=bool(data.get("enabled", True)),
            speed=_clamp(float(data.get("speed", 7.0)), _SPEED_MIN, _SPEED_MAX),
            bezier=bezier,
            style=str(data.get("style", "")).strip(),
        )


@dataclass(frozen=True)
class AnimationsSettings:
    leaves: tuple[AnimationLeaf, ...]

    @classmethod
    def defaults(cls) -> "AnimationsSettings":
        return cls(leaves=tuple(
            AnimationLeaf(name=name, enabled=enabled, speed=speed, bezier=bezier, style=style)
            for name, enabled, speed, bezier, style in _DEFAULTS
        ))

    def to_dict(self) -> dict:
        return {"animations": [leaf.to_dict() for leaf in self.leaves]}

    @classmethod
    def from_dict(cls, data: dict) -> "AnimationsSettings":
        raw = data.get("animations", [])
        provided = {
            str(item.get("name")): AnimationLeaf.from_dict(item)
            for item in raw
            if isinstance(item, dict) and str(item.get("name")) in CONFIGURABLE_LEAVES
        }
        # Orden y completitud fijados por el catálogo: claves ausentes → default.
        defaults_by_name = {leaf.name: leaf for leaf in cls.defaults().leaves}
        return cls(leaves=tuple(
            provided.get(name, defaults_by_name[name]) for name in CONFIGURABLE_LEAVES
        ))
