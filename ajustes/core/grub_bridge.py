import os
import shlex
import subprocess
import tempfile
from typing import Any, Callable, Protocol

from ajustes.config import DEFAULT_GRUB
from ajustes.core.errors import GrubError

# pkexec: 126 = autenticación cancelada/denegada, 127 = no pudo ejecutar.
_PKEXEC_AUTH_FAILED = (126, 127)

DEFAULT_GRUB_PATH = str(DEFAULT_GRUB)


class GrubBridge(Protocol):
    """Frontera privilegiada: instala /etc/default/grub y regenera grub.cfg."""

    def apply(self, content: str) -> None: ...


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class RealGrubBridge:
    """Escribe el nuevo /etc/default/grub y ejecuta update-grub en un único pkexec.

    El contenido se escribe a un temp del usuario y se instala como root; así sólo
    hay un prompt de autenticación para ambas operaciones.
    """

    def __init__(
        self,
        run: Callable[[list[str]], Any] = _run_captured,
        default_grub_path: str = DEFAULT_GRUB_PATH,
    ):
        self._run = run
        self._path = default_grub_path

    def apply(self, content: str) -> None:
        fd, tmp = tempfile.mkstemp(prefix="grub_ajustes_", suffix=".conf")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            script = (
                f"install -m 0644 {shlex.quote(tmp)} {shlex.quote(self._path)} "
                f"&& update-grub"
            )
            try:
                result = self._run(["pkexec", "bash", "-c", script])
            except FileNotFoundError as error:
                raise GrubError("pkexec o bash no encontrados.") from error
            if result.returncode in _PKEXEC_AUTH_FAILED:
                raise GrubError("Autenticación cancelada o denegada.")
            if result.returncode != 0:
                snippet = (result.stdout or "")[:200]
                raise GrubError(f"update-grub falló (código {result.returncode}): {snippet!r}")
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
