from dataclasses import dataclass

from ajustes.core.config_store import ConfigStore
from ajustes.core.errors import BindConflictError
from ajustes.core.hyprland_bridge import HyprlandBridge
from ajustes.core.keybindings import (
    Bind,
    CatalogBind,
    KeybindingsSettings,
    detect_conflict,
    validate_bind,
)


@dataclass(frozen=True)
class ApplyResult:
    settings: KeybindingsSettings
    applied_live: bool


class ApplyKeybindings:
    """Alta/edición/baja de binds: valida → conflicto → JSON → hyprctl reload."""

    def __init__(self, store: ConfigStore, bridge: HyprlandBridge):
        self._store = store
        self._bridge = bridge

    def save(
        self,
        settings: KeybindingsSettings,
        bind: Bind,
        catalog: list[CatalogBind],
    ) -> ApplyResult:
        validate_bind(bind)
        clash = detect_conflict(bind, settings, catalog, exclude_id=bind.id)
        if clash is not None:
            raise BindConflictError(clash)
        return self._persist(settings.upsert(bind))

    def delete(self, settings: KeybindingsSettings, bind_id: str) -> ApplyResult:
        return self._persist(settings.remove(bind_id))

    def set_enabled(
        self, settings: KeybindingsSettings, bind_id: str, enabled: bool
    ) -> ApplyResult:
        return self._persist(settings.with_enabled(bind_id, enabled))

    def _persist(self, settings: KeybindingsSettings) -> ApplyResult:
        self._store.write("keybindings", settings.to_dict())
        applied_live = self._bridge.is_available()
        if applied_live:
            self._bridge.reload()
        return ApplyResult(settings=settings, applied_live=applied_live)
