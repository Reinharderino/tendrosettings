import json
import os
import time
from pathlib import Path

from ajustes.core.errors import CorruptSettingsError

BACKUP_DIR_NAME = ".backups"
MAX_BACKUPS_PER_FILE = 10


def timestamped_backup(file_path: Path, backups_dir: Path) -> None:
    """Copia `file_path` (si existe) a `backups_dir` con un sello de tiempo único."""
    if not file_path.exists():
        return
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1_000_000_000:09d}"
    backup_path = backups_dir / f"{file_path.stem}.{stamp}{file_path.suffix}"
    backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")


def backup_and_write(file_path: Path, content: str, backups_dir: Path) -> None:
    """Respalda el contenido actual de `file_path` y escribe el nuevo de forma atómica."""
    timestamped_backup(file_path, backups_dir)
    _atomic_write(file_path, content)


def _atomic_write(file_path: Path, content: str) -> None:
    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, file_path)


class ConfigStore:
    """Lee y escribe los JSON de ~/.config/hypr/settings/ con backups."""

    def __init__(self, settings_dir: Path):
        self._settings_dir = settings_dir

    def read(self, name: str) -> dict | None:
        file_path = self._settings_dir / f"{name}.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CorruptSettingsError(file_path, str(error)) from error
        if not isinstance(data, dict):
            raise CorruptSettingsError(file_path, "la raíz no es un objeto JSON")
        return data

    def write(self, name: str, data: dict) -> None:
        self._settings_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._settings_dir / f"{name}.json"
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        backup_and_write(file_path, content, self.backups_dir())
        self._prune_backups(name)

    def backups_for(self, name: str) -> list[Path]:
        """Backups de `name`, el más reciente primero (solo los .json del store)."""
        if not self.backups_dir().exists():
            return []
        return sorted(
            self.backups_dir().glob(f"{name}.*.json"), reverse=True
        )

    def restore_latest_backup(self, name: str) -> bool:
        """Sobreescribe el archivo vivo con el último backup, SIN respaldarlo antes.

        Pensado para recuperación de corrupción: el archivo vivo se asume inservible.
        """
        backups = self.backups_for(name)
        if not backups:
            return False
        _atomic_write(self._settings_dir / f"{name}.json", backups[0].read_text(encoding="utf-8"))
        return True

    def backups_dir(self) -> Path:
        return self._settings_dir / BACKUP_DIR_NAME

    def _prune_backups(self, name: str) -> None:
        for stale in self.backups_for(name)[MAX_BACKUPS_PER_FILE:]:
            stale.unlink()
