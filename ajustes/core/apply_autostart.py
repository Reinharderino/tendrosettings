from ajustes.core.autostart import AutostartSettings
from ajustes.core.config_store import ConfigStore


class ApplyAutostart:
    """Persiste AutostartSettings a JSON. Sin reload: toma efecto al próximo
    inicio de sesión (hyprctl reload no re-dispara hyprland.start, y relanzar
    mid-sesión duplicaría apps ya abiertas)."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def execute(self, settings: AutostartSettings) -> AutostartSettings:
        self._store.write("autostart", settings.to_dict())
        return settings
