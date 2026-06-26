from pathlib import Path


class AjustesError(Exception):
    """Base de los errores de dominio de hypr-ajustes."""


class CorruptSettingsError(AjustesError):
    """Un archivo de settings existe pero no es JSON-objeto válido."""

    def __init__(self, file_path: Path, reason: str):
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"{file_path}: {reason}")


class HyprlandUnavailableError(AjustesError):
    """No hay sesión Hyprland a la que aplicar cambios en vivo."""


class ThemingError(AjustesError):
    """Falló la aplicación de un tema/colores a las apps (KDE/GTK)."""


class SnapshotError(AjustesError):
    """Falló una operación de snapshots (crear/borrar) o la autenticación."""


class GrubError(AjustesError):
    """Falló la escritura de /etc/default/grub, update-grub o la autenticación."""


class DualBootError(AjustesError):
    """Falló una operación de arranque (efibootmgr) o la autenticación."""


class CredentialError(AjustesError):
    """Falló una operación de credenciales/certificados (keyring, ssh, gpg, tls)."""


class InvalidWallpaperError(AjustesError):
    """La imagen elegida no existe o no es un formato soportado."""


class InvalidBindError(AjustesError):
    """El bind del formulario no cumple las reglas del dominio."""


class BindConflictError(AjustesError):
    """La combinación ya está asignada a otro bind (JSON o sistema)."""

    def __init__(self, conflicting):
        self.conflicting = conflicting
        super().__init__("la combinación ya está en uso")
