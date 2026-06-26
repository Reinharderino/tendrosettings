import os
import subprocess
from collections.abc import Mapping
from typing import Any, Callable, Protocol

from ajustes.core.errors import ThemingError

_INTERFACE = "org.gnome.desktop.interface"


class ThemingBridge(Protocol):
    """Frontera con las herramientas de tema del sistema (KDE/GTK)."""

    def apply_kde_scheme(self, scheme_name: str) -> None: ...
    def apply_gtk(self, prefer_dark: bool, accent_name: str | None) -> None: ...


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class KdeGtkBridge:
    """Aplica colores vía plasma-apply-colorscheme (KDE/Qt) y gsettings (GTK)."""

    def __init__(
        self,
        run: Callable[[list[str]], Any] = _run_captured,
        env: Mapping[str, str] | None = None,
    ):
        self._run = run
        self._env = os.environ if env is None else env

    def _exec(self, args: list[str], what: str) -> None:
        try:
            result = self._run(args)
        except FileNotFoundError as error:
            raise ThemingError(f"{args[0]} no encontrado — ¿instalado?") from error
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise ThemingError(f"{what} falló (código {result.returncode}): {snippet!r}")

    def apply_kde_scheme(self, scheme_name: str) -> None:
        """Aplica el esquema de color a la sesión: escribe kdeglobals y notifica
        a las apps KDE/Qt abiertas (Dolphin, etc.)."""
        self._exec(["plasma-apply-colorscheme", scheme_name], "plasma-apply-colorscheme")

    def apply_gtk(self, prefer_dark: bool, accent_name: str | None) -> None:
        """Sincroniza apps GTK: preferencia claro/oscuro y, si se da, acento con nombre."""
        scheme = "prefer-dark" if prefer_dark else "prefer-light"
        self._exec(
            ["gsettings", "set", _INTERFACE, "color-scheme", scheme],
            "gsettings color-scheme",
        )
        if accent_name:
            self._exec(
                ["gsettings", "set", _INTERFACE, "accent-color", accent_name],
                "gsettings accent-color",
            )
