from pathlib import Path

from ajustes.core.config_store import timestamped_backup
from ajustes.core.grub import replace_cmdline_in_grub
from ajustes.core.grub_bridge import GrubBridge


class ApplyGrub:
    """Aplica un nuevo GRUB_CMDLINE_LINUX_DEFAULT: respalda /etc/default/grub,
    reemplaza sólo esa línea y delega la escritura privilegiada + update-grub en el bridge."""

    def __init__(self, bridge: GrubBridge, default_grub_path: Path, backups_dir: Path):
        self._bridge = bridge
        self._path = default_grub_path
        self._backups_dir = backups_dir

    def execute(self, new_cmdline: str) -> None:
        content = self._path.read_text(encoding="utf-8")
        new_content = replace_cmdline_in_grub(content, new_cmdline)
        timestamped_backup(self._path, self._backups_dir)
        self._bridge.apply(new_content)
