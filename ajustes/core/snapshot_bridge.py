import subprocess
from typing import Any, Callable, Protocol

from ajustes.core.errors import SnapshotError

# pkexec devuelve 126 si la autenticación se cancela/deniega, 127 si no pudo
# ejecutar el programa (p.ej. sin agente polkit).
_PKEXEC_AUTH_FAILED = (126, 127)


class SnapshotBridge(Protocol):
    """Frontera con la herramienta de snapshots (operaciones privilegiadas)."""

    def create_snapshot(self, description: str) -> int: ...
    def delete_snapshots(self, numbers: list[int]) -> None: ...


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class SnapperBridge:
    """Crea/borra snapshots vía `pkexec snapper` (el listado se hace sin privilegios
    leyendo /.snapshots/*/info.xml; ver core.snapshots.read_snapshots)."""

    def __init__(
        self,
        run: Callable[[list[str]], Any] = _run_captured,
        config: str = "root",
    ):
        self._run = run
        self._config = config

    def _snapper(self, *args: str) -> Any:
        cmd = ["pkexec", "snapper", "-c", self._config, *args]
        try:
            result = self._run(cmd)
        except FileNotFoundError as error:
            raise SnapshotError("pkexec o snapper no encontrados.") from error
        if result.returncode in _PKEXEC_AUTH_FAILED:
            raise SnapshotError("Autenticación cancelada o denegada.")
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise SnapshotError(f"snapper falló (código {result.returncode}): {snippet!r}")
        return result

    def create_snapshot(self, description: str) -> int:
        """Crea un snapshot 'single' y devuelve su número."""
        result = self._snapper("create", "-d", description, "--print-number")
        out = (result.stdout or "").strip()
        if not out.isdigit():
            raise SnapshotError(f"snapper no devolvió un número de snapshot: {out!r}")
        return int(out)

    def delete_snapshots(self, numbers: list[int]) -> None:
        if not numbers:
            return
        self._snapper("delete", *(str(n) for n in numbers))
