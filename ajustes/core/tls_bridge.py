import subprocess
from typing import Any, Callable

from ajustes.core.errors import CredentialError
from ajustes.core.tls_certs import CaCert, parse_trust_list

_PKEXEC_AUTH_FAILED = (126, 127)


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class TlsBridge:
    """Lista anclas de confianza CA (p11-kit). Añadir/quitar requiere privilegio."""

    def __init__(self, run: Callable[[list[str]], Any] = _run_captured):
        self._run = run

    def list_cas(self) -> list[CaCert]:
        try:
            result = self._run(["trust", "list"])
        except FileNotFoundError as error:
            raise CredentialError("trust (p11-kit) no encontrado.") from error
        if result.returncode != 0:
            raise CredentialError(f"trust list falló (código {result.returncode}).")
        return parse_trust_list(result.stdout or "")

    def add_anchor(self, cert_path: str) -> None:
        self._pkexec_trust("anchor", cert_path)

    def remove_anchor(self, uri: str) -> None:
        self._pkexec_trust("anchor", "--remove", uri)

    def _pkexec_trust(self, *args: str) -> None:
        try:
            result = self._run(["pkexec", "trust", *args])
        except FileNotFoundError as error:
            raise CredentialError("pkexec o trust no encontrados.") from error
        if result.returncode in _PKEXEC_AUTH_FAILED:
            raise CredentialError("Autenticación cancelada o denegada.")
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise CredentialError(f"trust falló (código {result.returncode}): {snippet!r}")
