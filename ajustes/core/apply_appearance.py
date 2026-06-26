from dataclasses import dataclass

from ajustes.core.appearance import AppearanceSettings
from ajustes.core.config_store import ConfigStore
from ajustes.core.hyprland_bridge import HyprlandBridge


@dataclass(frozen=True)
class ApplyResult:
    settings: AppearanceSettings
    applied_live: bool


class ApplyAppearance:
    """Persiste AppearanceSettings a appearance.json y recarga Hyprland.

    El loader Lua (settings.appearance) relee el JSON en el reload y aplica
    los valores vía hl.config, sobreescribiendo los defaults de hyprland.lua.
    """

    def __init__(self, store: ConfigStore, bridge: HyprlandBridge):
        self._store = store
        self._bridge = bridge

    def execute(self, settings: AppearanceSettings) -> ApplyResult:
        self._store.write("appearance", settings.to_dict())
        applied_live = self._bridge.is_available()
        if applied_live:
            self._bridge.reload()
        return ApplyResult(settings=settings, applied_live=applied_live)
