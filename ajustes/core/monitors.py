import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class MonitorSpec:
    name: str
    mode: str
    scale: float
    x: int
    y: int
    transform: int
    enabled: bool = True

    TRANSFORM_LABELS: ClassVar[tuple[str, ...]] = (
        "Normal", "90°", "180°", "270°",
        "Flip", "90° + Flip", "180° + Flip", "270° + Flip",
    )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "mode": self.mode,
            "scale": self.scale,
            "x": self.x,
            "y": self.y,
            "transform": self.transform,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MonitorSpec":
        transform = int(data.get("transform", 0))
        if transform not in range(8):
            transform = 0
        scale = float(data.get("scale", 1.0))
        scale = max(0.5, min(3.0, scale))
        return cls(
            name=str(data.get("name", "")),
            mode=str(data.get("mode", "preferred")),
            scale=scale,
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            transform=transform,
            enabled=bool(data.get("enabled", True)),
        )


@dataclass(frozen=True)
class PowerSettings:
    suspend_minutes: int = 5
    off_minutes: int = 15

    def __post_init__(self) -> None:
        off, suspend = self.off_minutes, self.suspend_minutes
        if off > 0 and suspend > 0 and off <= suspend:
            raise ValueError(
                f"off_minutes ({off}) debe ser mayor que suspend_minutes ({suspend})"
            )

    def to_dict(self) -> dict:
        return {
            "suspend_minutes": self.suspend_minutes,
            "off_minutes": self.off_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PowerSettings":
        suspend = max(0, int(data.get("suspend_minutes", 5)))
        off = max(0, int(data.get("off_minutes", 15)))
        return cls(suspend_minutes=suspend, off_minutes=off)


@dataclass(frozen=True)
class MonitorSettings:
    monitors: tuple[MonitorSpec, ...]
    power: PowerSettings

    def to_dict(self) -> dict:
        return {
            "monitors": [m.to_dict() for m in self.monitors],
            "power": self.power.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MonitorSettings":
        raw_monitors = data.get("monitors", [])
        monitors = tuple(
            MonitorSpec.from_dict(m)
            for m in raw_monitors
            if isinstance(m, dict)
        )
        power_data = data.get("power", {})
        power = PowerSettings.from_dict(
            power_data if isinstance(power_data, dict) else {}
        )
        return cls(monitors=monitors, power=power)


def parse_modes(available_modes: list[str]) -> dict[str, list[float]]:
    """Agrupa modos disponibles por resolución.

    Returns {resolution: [refresh_hz, ...]} con tasas ordenadas descendente.
    """
    result: dict[str, list[float]] = {}
    pattern = re.compile(r"^(\d+x\d+)@([\d.]+)Hz$")
    for mode_str in available_modes:
        match = pattern.match(mode_str)
        if match:
            res, rate = match.group(1), float(match.group(2))
            result.setdefault(res, []).append(rate)
    for rates in result.values():
        rates.sort(reverse=True)
    return result


def mode_string(resolution: str, refresh_hz: float) -> str:
    """Reconstruye el string de modo que espera Hyprland."""
    return f"{resolution}@{refresh_hz:.2f}Hz"


def generate_hypridle_conf(power: PowerSettings) -> str:
    """Genera el contenido de hypridle.conf desde la configuración de energía."""
    lines = ["# Generado por hypr-ajustes — no editar manualmente", ""]
    if power.suspend_minutes > 0:
        t = power.suspend_minutes * 60
        lines += [
            "listener {",
            f"    timeout = {t}",
            "    on-timeout = hyprctl dispatch dpms off",
            "    on-resume = hyprctl dispatch dpms on",
            "}",
            "",
        ]
    if power.off_minutes > 0:
        t = power.off_minutes * 60
        lines += [
            "listener {",
            f"    timeout = {t}",
            "    on-timeout = systemctl suspend",
            "}",
            "",
        ]
    return "\n".join(lines)
