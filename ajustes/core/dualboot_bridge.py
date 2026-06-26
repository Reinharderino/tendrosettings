import subprocess
from typing import Any, Callable, Protocol

from ajustes.core.dualboot import EfiBootState, parse_efibootmgr
from ajustes.core.errors import DualBootError

_PKEXEC_AUTH_FAILED = (126, 127)


class DualBootBridge(Protocol):
    def read_state(self) -> EfiBootState: ...
    def set_boot_next(self, num: str) -> None: ...
    def set_boot_order(self, numbers: list[str]) -> None: ...
    def reboot(self) -> None: ...


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class EfibootmgrBridge:
    """Lee/escribe entradas de arranque UEFI. La lectura no requiere privilegios;
    los cambios (BootNext/BootOrder) van vía pkexec."""

    def __init__(self, run: Callable[[list[str]], Any] = _run_captured):
        self._run = run

    def read_state(self) -> EfiBootState:
        try:
            result = self._run(["efibootmgr"])
        except FileNotFoundError as error:
            raise DualBootError("efibootmgr no encontrado.") from error
        if result.returncode != 0:
            raise DualBootError(f"efibootmgr falló (código {result.returncode}).")
        return parse_efibootmgr(result.stdout)

    def _pkexec_efibootmgr(self, *args: str) -> None:
        try:
            result = self._run(["pkexec", "efibootmgr", *args])
        except FileNotFoundError as error:
            raise DualBootError("pkexec o efibootmgr no encontrados.") from error
        if result.returncode in _PKEXEC_AUTH_FAILED:
            raise DualBootError("Autenticación cancelada o denegada.")
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise DualBootError(f"efibootmgr falló (código {result.returncode}): {snippet!r}")

    def set_boot_next(self, num: str) -> None:
        """Arranca esa entrada SÓLO en el próximo reinicio (BootNext)."""
        self._pkexec_efibootmgr("--bootnext", num)

    def set_boot_order(self, numbers: list[str]) -> None:
        """Fija el orden de arranque persistente."""
        if not numbers:
            return
        self._pkexec_efibootmgr("--bootorder", ",".join(numbers))

    def reboot(self) -> None:
        try:
            self._run(["systemctl", "reboot"])
        except FileNotFoundError as error:
            raise DualBootError("systemctl no encontrado.") from error
