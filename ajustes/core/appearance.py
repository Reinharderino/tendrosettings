import re
from dataclasses import dataclass

# Formato de color de Hyprland: rgb(rrggbb) o rgba(rrggbbaa), case-insensitive.
_COLOR_RE = re.compile(r"^rgba?\([0-9a-f]{6}([0-9a-f]{2})?\)$", re.IGNORECASE)

# Rangos de saneo (clamp). Fuera de rango se recorta, no se rechaza: la sesión
# nunca debe romperse por un valor extremo en el JSON.
_GAPS_MAX = 100
_BORDER_MAX = 20
_ROUNDING_MAX = 50
_BLUR_SIZE_MIN, _BLUR_SIZE_MAX = 1, 20
_BLUR_PASSES_MIN, _BLUR_PASSES_MAX = 1, 10
_ANGLE_MAX = 360

# Defaults = bloque LOOK AND FEEL hardcodeado en hyprland.lua. Mantener en sintonía.
_DEFAULT_ACTIVE_1 = "rgba(33ccffee)"
_DEFAULT_ACTIVE_2 = "rgba(00ff99ee)"
_DEFAULT_INACTIVE = "rgba(595959aa)"


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def hypr_color_to_rgba_floats(color: str) -> tuple[float, float, float, float]:
    """Convierte un color de Hyprland (rgb/rgba hex) a floats RGBA en [0, 1].

    Pensado para inicializar el color picker. Color inválido → negro opaco.
    """
    if isinstance(color, str) and _COLOR_RE.match(color.strip()):
        hexpart = color.strip().lower().split("(", 1)[1].rstrip(")")
        r = int(hexpart[0:2], 16) / 255
        g = int(hexpart[2:4], 16) / 255
        b = int(hexpart[4:6], 16) / 255
        a = int(hexpart[6:8], 16) / 255 if len(hexpart) == 8 else 1.0
        return (r, g, b, a)
    return (0.0, 0.0, 0.0, 1.0)


def rgba_floats_to_hypr_color(r: float, g: float, b: float, a: float) -> str:
    """Convierte floats RGBA en [0, 1] al formato rgba(rrggbbaa) de Hyprland.

    Valores fuera de rango se recortan a [0, 1] (lo que entrega Gdk.RGBA).
    """
    def byte(value: float) -> int:
        return round(max(0.0, min(1.0, value)) * 255)

    return f"rgba({byte(r):02x}{byte(g):02x}{byte(b):02x}{byte(a):02x})"


def _coerce_color(value, fallback: str) -> str:
    if isinstance(value, str) and _COLOR_RE.match(value.strip()):
        return value.strip().lower()
    return fallback


@dataclass(frozen=True)
class AppearanceSettings:
    gaps_in: int
    gaps_out: int
    border_size: int
    rounding: int
    blur_enabled: bool
    blur_size: int
    blur_passes: int
    animations_enabled: bool
    active_color_1: str
    active_color_2: str
    gradient_angle: int
    inactive_color: str

    @classmethod
    def defaults(cls) -> "AppearanceSettings":
        return cls(
            gaps_in=5, gaps_out=10, border_size=2,
            rounding=10, blur_enabled=True, blur_size=3, blur_passes=1,
            animations_enabled=True,
            active_color_1=_DEFAULT_ACTIVE_1, active_color_2=_DEFAULT_ACTIVE_2,
            gradient_angle=45, inactive_color=_DEFAULT_INACTIVE,
        )

    def to_dict(self) -> dict:
        return {
            "gaps_in": self.gaps_in,
            "gaps_out": self.gaps_out,
            "border_size": self.border_size,
            "rounding": self.rounding,
            "blur_enabled": self.blur_enabled,
            "blur_size": self.blur_size,
            "blur_passes": self.blur_passes,
            "animations_enabled": self.animations_enabled,
            "active_color_1": self.active_color_1,
            "active_color_2": self.active_color_2,
            "gradient_angle": self.gradient_angle,
            "inactive_color": self.inactive_color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppearanceSettings":
        d = cls.defaults()
        return cls(
            gaps_in=_clamp(int(data.get("gaps_in", d.gaps_in)), 0, _GAPS_MAX),
            gaps_out=_clamp(int(data.get("gaps_out", d.gaps_out)), 0, _GAPS_MAX),
            border_size=_clamp(int(data.get("border_size", d.border_size)), 0, _BORDER_MAX),
            rounding=_clamp(int(data.get("rounding", d.rounding)), 0, _ROUNDING_MAX),
            blur_enabled=bool(data.get("blur_enabled", d.blur_enabled)),
            blur_size=_clamp(int(data.get("blur_size", d.blur_size)), _BLUR_SIZE_MIN, _BLUR_SIZE_MAX),
            blur_passes=_clamp(int(data.get("blur_passes", d.blur_passes)), _BLUR_PASSES_MIN, _BLUR_PASSES_MAX),
            animations_enabled=bool(data.get("animations_enabled", d.animations_enabled)),
            active_color_1=_coerce_color(data.get("active_color_1"), d.active_color_1),
            active_color_2=_coerce_color(data.get("active_color_2"), d.active_color_2),
            gradient_angle=_clamp(int(data.get("gradient_angle", d.gradient_angle)), 0, _ANGLE_MAX),
            inactive_color=_coerce_color(data.get("inactive_color"), d.inactive_color),
        )
