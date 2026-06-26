from dataclasses import dataclass

from ajustes.core.animations import AnimationsSettings
from ajustes.core.config_store import ConfigStore
from ajustes.core.hyprland_bridge import HyprlandBridge


@dataclass(frozen=True)
class ApplyResult:
    settings: AnimationsSettings
    applied_live: bool


class ApplyAnimations:
    """Persiste AnimationsSettings a animations.json y recarga Hyprland.

    El loader Lua (settings.animations) relee el JSON en el reload y aplica cada
    leaf vía hl.animation, sobreescribiendo los hl.animation de hyprland.lua.
    """

    def __init__(self, store: ConfigStore, bridge: HyprlandBridge):
        self._store = store
        self._bridge = bridge

    def execute(self, settings: AnimationsSettings) -> ApplyResult:
        self._store.write("animations", settings.to_dict())
        applied_live = self._bridge.is_available()
        if applied_live:
            self._bridge.reload()
        return ApplyResult(settings=settings, applied_live=applied_live)
