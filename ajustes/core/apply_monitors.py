from dataclasses import dataclass
from pathlib import Path

from ajustes.core.config_store import ConfigStore, backup_and_write
from ajustes.core.hyprland_bridge import HyprlandBridge
from ajustes.core.monitors import MonitorSettings, generate_hypridle_conf


@dataclass(frozen=True)
class ApplyResult:
    settings: MonitorSettings
    applied_live: bool


class ApplyMonitors:
    """Persiste MonitorSettings a JSON + hypridle.conf y recarga Hyprland."""

    def __init__(
        self,
        store: ConfigStore,
        bridge: HyprlandBridge,
        hypridle_conf_path: Path,
    ):
        self._store = store
        self._bridge = bridge
        self._hypridle_conf_path = hypridle_conf_path

    def execute(self, settings: MonitorSettings) -> ApplyResult:
        self._store.write("monitors", settings.to_dict())
        conf_content = generate_hypridle_conf(settings.power)
        backup_and_write(
            self._hypridle_conf_path,
            conf_content,
            backups_dir=self._store.backups_dir(),
        )
        applied_live = self._bridge.is_available()
        if applied_live:
            self._bridge.restart_hypridle()
            self._bridge.reload()
        return ApplyResult(settings=settings, applied_live=applied_live)
