from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# Formatos que hyprpaper puede renderizar.
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
# Formatos que requieren swww/mpvpaper (toggle "animado" del spec).
ANIMATED_EXTENSIONS = {".gif", ".mp4", ".webm"}


@dataclass(frozen=True)
class GalleryImage:
    path: Path
    animated: bool


def scan_folders(folders: Iterable[str]) -> list[GalleryImage]:
    """Imágenes de las carpetas dadas (no recursivo), ordenadas por nombre.

    Carpetas inexistentes, repetidas o inaccesibles se ignoran en silencio:
    el caller (la galería GTK) nunca debe crashear por un escaneo.
    """
    images: list[GalleryImage] = []
    seen: set[Path] = set()
    for folder in folders:
        directory = Path(folder).expanduser().resolve()
        if directory in seen or not directory.is_dir():
            continue
        seen.add(directory)
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_file():
                continue
            suffix = entry.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                images.append(GalleryImage(path=entry, animated=False))
            elif suffix in ANIMATED_EXTENSIONS:
                images.append(GalleryImage(path=entry, animated=True))
    return sorted(images, key=lambda image: image.path.name.casefold())
