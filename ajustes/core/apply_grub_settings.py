from pathlib import Path

from ajustes.core.config_store import timestamped_backup
from ajustes.core.grub import set_grub_key
from ajustes.core.grub_bridge import GrubBridge


class ApplyGrubSettings:
    """Aplica varias claves de /etc/default/grub (GRUB_TIMEOUT, GRUB_DISABLE_OS_PROBER…):
    respalda el fichero, reemplaza cada clave y delega la escritura privilegiada +
    update-grub en el bridge."""

    def __init__(self, bridge: GrubBridge, default_grub_path: Path, backups_dir: Path):
        self._bridge = bridge
        self._path = default_grub_path
        self._backups_dir = backups_dir

    def execute(self, updates: dict[str, str]) -> None:
        content = self._path.read_text(encoding="utf-8")
        for key, rhs in updates.items():
            content = set_grub_key(content, key, rhs)
        timestamped_backup(self._path, self._backups_dir)
        self._bridge.apply(content)
