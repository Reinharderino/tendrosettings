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

    def _exec(self, args: list[str], what: str, *, optional: bool = False) -> None:
        """optional=True: si el binario no existe, se omite en silencio. Un binario
        presente que falla SIEMPRE lanza, exista o no la bandera."""
        try:
            result = self._run(args)
        except FileNotFoundError as error:
            if optional:
                return
            raise ThemingError(f"{args[0]} no encontrado — ¿instalado?") from error
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise ThemingError(f"{what} falló (código {result.returncode}): {snippet!r}")

    def apply_kde_scheme(self, scheme_name: str) -> None:
        """Notifica el esquema a las apps KDE/Qt abiertas (Dolphin, Okular).

        kdeglobals lo escribe el use-case, no esta llamada: acá sólo se avisa a
        las apps vivas. En una máquina sin Plasma el binario no existe y no hay a
        quién avisar — las apps Qt toman el color al reabrirse. Por eso es
        `optional`: ausencia de Plasma no debe abortar el resto del apply (GTK,
        theme.css), que es lo que pasaba tras eliminar KDE.
        """
        self._exec(
            ["plasma-apply-colorscheme", scheme_name],
            "plasma-apply-colorscheme",
            optional=True,
        )

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
