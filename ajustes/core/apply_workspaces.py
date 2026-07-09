from dataclasses import dataclass

from ajustes.core.config_store import ConfigStore
from ajustes.core.hyprland_bridge import HyprlandBridge
from ajustes.core.workspaces import WorkspaceSettings


@dataclass(frozen=True)
class ApplyResult:
    settings: WorkspaceSettings
    applied_live: bool


class ApplyWorkspaces:
    """Persiste WorkspaceSettings a JSON y recarga Hyprland."""

    def __init__(self, store: ConfigStore, bridge: HyprlandBridge):
        self._store = store
        self._bridge = bridge

    def execute(self, settings: WorkspaceSettings) -> ApplyResult:
        self._store.write("workspaces", settings.to_dict())
        applied_live = self._bridge.is_available()
        if applied_live:
            self._bridge.reload()
        return ApplyResult(settings=settings, applied_live=applied_live)
