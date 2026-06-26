import json
import os
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Protocol

from ajustes import config
from ajustes.core.errors import HyprlandUnavailableError

ANSI_ESCAPES = re.compile(r"\x1b\[[0-9;]*m")

# Aplicador agnóstico al archivo y al binario (swww/awww) para wallpapers animados.
# Versionado en el repo y enlazado a ~/.config/hypr/scripts/ (igual que settings/init.lua).
ANIMATED_WALLPAPER_SCRIPT = str(config.ANIMATED_WALLPAPER_SCRIPT)


class HyprlandBridge(Protocol):
    """Frontera con la sesión Hyprland. Las capas superiores solo conocen esto."""

    def is_available(self) -> bool: ...
    def monitor_names(self) -> list[str]: ...
    def set_wallpaper(self, monitor: str, image_path: str) -> None: ...
    def set_animated_wallpaper(
        self, monitor: str, image_path: str, fit_mode: str = "cover"
    ) -> None: ...
    def verify_config(self) -> str | None: ...
    def get_binds(self) -> list[dict]: ...
    def reload(self) -> None: ...
    def monitors_info(self) -> list[dict]: ...
    def restart_hypridle(self) -> None: ...


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class HyprctlBridge:
    """Implementación real sobre hyprctl/Hyprland vía subprocess."""

    def __init__(
        self,
        run: Callable[[list[str]], Any] = _run_captured,
        env: Mapping[str, str] | None = None,
    ):
        self._run = run
        self._env = os.environ if env is None else env

    def is_available(self) -> bool:
        return bool(self._env.get("HYPRLAND_INSTANCE_SIGNATURE"))

    def monitor_names(self) -> list[str]:
        """Devuelve los nombres de monitores activos.

        Traduce fallos de infraestructura (binario ausente, IPC roto,
        JSON inválido) a HyprlandUnavailableError para que las capas
        superiores no dependan de excepciones de subprocess/json.
        """
        try:
            result = self._run(["hyprctl", "monitors", "-j"])
        except FileNotFoundError as error:
            raise HyprlandUnavailableError(
                "hyprctl no encontrado — ¿Hyprland está instalado?"
            ) from error

        if result.returncode != 0:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl monitors falló (código {result.returncode}): {snippet!r}"
            )

        try:
            return [monitor["name"] for monitor in json.loads(result.stdout)]
        except json.JSONDecodeError as error:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl monitors devolvió JSON inválido: {snippet!r}"
            ) from error

    def monitors_info(self) -> list[dict]:
        """Devuelve la salida completa de `hyprctl monitors -j`."""
        try:
            result = self._run(["hyprctl", "monitors", "-j"])
        except FileNotFoundError as error:
            raise HyprlandUnavailableError(
                "hyprctl no encontrado — ¿Hyprland está instalado?"
            ) from error
        if result.returncode != 0:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl monitors falló (código {result.returncode}): {snippet!r}"
            )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl monitors devolvió JSON inválido: {snippet!r}"
            ) from error
        if not isinstance(data, list):
            raise HyprlandUnavailableError("hyprctl monitors no devolvió una lista")
        return data

    def set_wallpaper(self, monitor: str, image_path: str) -> None:
        """Aplica el fondo de pantalla en el monitor indicado vía hyprpaper IPC.

        Lanza HyprlandUnavailableError si el binario falta o el IPC reporta error.
        """
        try:
            result = self._run(
                ["hyprctl", "hyprpaper", "wallpaper", f"{monitor},{image_path}"]
            )
        except FileNotFoundError as error:
            raise HyprlandUnavailableError(
                "hyprctl no encontrado — ¿Hyprland está instalado?"
            ) from error

        if result.returncode != 0:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"set_wallpaper IPC falló (código {result.returncode}): {snippet!r}"
            )

    def verify_config(self) -> str | None:
        """Verifica la configuración de Hyprland.

        Devuelve None si es correcta, o la salida del proceso (sin códigos ANSI)
        si hay errores.
        """
        result = self._run(["Hyprland", "--verify-config"])
        if result.returncode == 0 and "config ok" in result.stdout:
            return None
        return ANSI_ESCAPES.sub("", result.stdout)

    def get_binds(self) -> list[dict]:
        """Salida cruda de `hyprctl binds -j`; la traducción al dominio vive
        en core/keybindings.parse_catalog (el bridge no conoce el modelo)."""
        try:
            result = self._run(["hyprctl", "binds", "-j"])
        except FileNotFoundError as error:
            raise HyprlandUnavailableError(
                "hyprctl no encontrado — ¿Hyprland está instalado?"
            ) from error
        if result.returncode != 0:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl binds falló (código {result.returncode}): {snippet!r}"
            )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl binds devolvió JSON inválido: {snippet!r}"
            ) from error
        if not isinstance(data, list):
            raise HyprlandUnavailableError("hyprctl binds no devolvió una lista")
        return data

    def reload(self) -> None:
        """Recarga la config de Hyprland (re-ejecuta hyprland.lua y el loader)."""
        try:
            result = self._run(["hyprctl", "reload"])
        except FileNotFoundError as error:
            raise HyprlandUnavailableError(
                "hyprctl no encontrado — ¿Hyprland está instalado?"
            ) from error
        if result.returncode != 0:
            snippet = result.stdout[:120]
            raise HyprlandUnavailableError(
                f"hyprctl reload falló (código {result.returncode}): {snippet!r}"
            )

    def restart_hypridle(self) -> None:
        """Reinicia el servicio hypridle del usuario. Si no está instalado, loguea y continúa."""
        try:
            result = self._run(["systemctl", "--user", "restart", "hypridle"])
        except FileNotFoundError:
            print("hypr-ajustes: systemctl no encontrado, hypridle no reiniciado")
            return
        if result.returncode != 0:
            print(
                f"hypr-ajustes: hypridle no reiniciado (código {result.returncode}) "
                "— ¿hypridle instalado?"
            )

    def set_animated_wallpaper(
        self, monitor: str, image_path: str, fit_mode: str = "cover"
    ) -> None:
        """Aplica un wallpaper animado/estático vía swww/awww en el monitor indicado,
        delegando en el script agnóstico wallpaper-swww.sh. hyprpaper no toca este output.

        Lanza HyprlandUnavailableError si el script falta o sale con error.
        """
        try:
            result = self._run(
                [
                    ANIMATED_WALLPAPER_SCRIPT,
                    "--output",
                    monitor,
                    "--fit",
                    fit_mode,
                    image_path,
                ]
            )
        except FileNotFoundError as error:
            raise HyprlandUnavailableError(
                f"{ANIMATED_WALLPAPER_SCRIPT} no encontrado — ¿hypr-ajustes instalado?"
            ) from error

        if result.returncode != 0:
            snippet = (result.stdout or "")[:120]
            raise HyprlandUnavailableError(
                f"set_animated_wallpaper falló (código {result.returncode}): {snippet!r}"
            )
