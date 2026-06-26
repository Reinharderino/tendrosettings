import re
from dataclasses import dataclass

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")

# Acentos con nombre de GNOME (libadwaita 1.6 / GNOME 47) y su hex de referencia.
# gsettings org.gnome.desktop.interface accent-color sólo acepta estos nombres.
GNOME_ACCENTS: dict[str, str] = {
    "blue": "#3584e4",
    "teal": "#2190a4",
    "green": "#3a944a",
    "yellow": "#c88800",
    "orange": "#ed5b00",
    "red": "#e62d42",
    "pink": "#d56199",
    "purple": "#9141ac",
    "slate": "#6f8396",
}

# Defaults = colores actuales del tema gótico en kdeglobals (R,G,B del [Colors:View]).
_DEFAULT_TEXT = "#e8d5b0"        # 232,213,176
_DEFAULT_BACKGROUND = "#0c0a08"  # 12,10,8
_DEFAULT_ACCENT = "#cd853f"      # 205,133,63


def normalize_hex(value) -> str | None:
    """Devuelve '#rrggbb' en minúsculas, o None si no es un hex de 6 dígitos."""
    if not isinstance(value, str):
        return None
    match = _HEX_RE.match(value.strip())
    return "#" + match.group(1).lower() if match else None


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = normalize_hex(hex_color) or "#000000"
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def hex_to_rgb_csv(hex_color: str) -> str:
    """'#rrggbb' -> 'R,G,B' (formato de color de KDE/kdeglobals)."""
    r, g, b = _hex_to_rgb(hex_color)
    return f"{r},{g},{b}"


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def relative_luminance(hex_color: str) -> float:
    """Luminancia relativa [0,1] (coeficientes Rec. 709)."""
    r, g, b = _hex_to_rgb(hex_color)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def is_dark(hex_color: str) -> bool:
    return relative_luminance(hex_color) < 0.5


def mix(hex_a: str, hex_b: str, t: float) -> str:
    """Mezcla lineal: t=0 -> a, t=1 -> b."""
    a, b = _hex_to_rgb(hex_a), _hex_to_rgb(hex_b)
    return _rgb_to_hex(*(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))


def nearest_gnome_accent(hex_color: str) -> str:
    """Nombre del acento GNOME más cercano por distancia euclídea en RGB."""
    target = _hex_to_rgb(hex_color)

    def dist(name: str) -> float:
        ref = _hex_to_rgb(GNOME_ACCENTS[name])
        return sum((target[i] - ref[i]) ** 2 for i in range(3))

    return min(GNOME_ACCENTS, key=dist)


@dataclass(frozen=True)
class AppColorsSettings:
    text_color: str
    background_color: str
    accent_color: str
    sync_gtk: bool

    @classmethod
    def defaults(cls) -> "AppColorsSettings":
        return cls(
            text_color=_DEFAULT_TEXT,
            background_color=_DEFAULT_BACKGROUND,
            accent_color=_DEFAULT_ACCENT,
            sync_gtk=True,
        )

    def to_dict(self) -> dict:
        return {
            "text_color": self.text_color,
            "background_color": self.background_color,
            "accent_color": self.accent_color,
            "sync_gtk": self.sync_gtk,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppColorsSettings":
        d = cls.defaults()
        return cls(
            text_color=normalize_hex(data.get("text_color")) or d.text_color,
            background_color=normalize_hex(data.get("background_color")) or d.background_color,
            accent_color=normalize_hex(data.get("accent_color")) or d.accent_color,
            sync_gtk=bool(data.get("sync_gtk", d.sync_gtk)),
        )


# Texto de contraste (blanco/negro) según luminancia de fondo: para texto sobre acento.
def _contrast_text(hex_bg: str) -> str:
    return "#000000" if not is_dark(hex_bg) else "#ffffff"


def generate_color_scheme(text: str, background: str, accent: str, name: str) -> str:
    """Genera un esquema de color KDE (.colors) completo desde 3 colores base.

    Deriva el resto (alternos, inactivos, decoración) por mezcla, de forma
    determinista. Compatible con plasma-apply-colorscheme.
    """
    csv = hex_to_rgb_csv
    bg = background
    fg = text
    bg_alt = mix(bg, fg, 0.06)          # fondo alterno: leve realce
    fg_inactive = mix(fg, bg, 0.4)      # texto atenuado
    decoration = accent
    sel_text = _contrast_text(accent)

    # Bloque común a la mayoría de grupos.
    def block(bg_normal: str, bg_alt_: str, fg_normal: str) -> dict[str, str]:
        return {
            "BackgroundNormal": csv(bg_normal),
            "BackgroundAlternate": csv(bg_alt_),
            "ForegroundNormal": csv(fg_normal),
            "ForegroundInactive": csv(fg_inactive),
            "ForegroundActive": csv(accent),
            "ForegroundLink": csv(accent),
            "ForegroundVisited": csv(mix(accent, bg, 0.3)),
            "ForegroundNegative": "218,68,83",
            "ForegroundNeutral": "246,116,0",
            "ForegroundPositive": "39,174,96",
            "DecorationFocus": csv(decoration),
            "DecorationHover": csv(decoration),
        }

    groups = {
        "Colors:View": block(bg, bg_alt, fg),
        "Colors:Window": block(bg, bg_alt, fg),
        "Colors:Button": block(mix(bg, fg, 0.08), bg_alt, fg),
        "Colors:Tooltip": block(bg, bg_alt, fg),
        "Colors:Complementary": block(bg, bg_alt, fg),
        "Colors:Header": block(bg, bg_alt, fg),
        "Colors:Selection": {
            **block(accent, accent, sel_text),
            "BackgroundNormal": csv(accent),
            "BackgroundAlternate": csv(accent),
            "ForegroundNormal": csv(sel_text),
        },
    }

    lines: list[str] = []
    for group, entries in groups.items():
        lines.append(f"[{group}]")
        for key, value in entries.items():
            lines.append(f"{key}={value}")
        lines.append("")
    lines.append("[General]")
    lines.append(f"Name={name}")
    lines.append("")
    return "\n".join(lines)
