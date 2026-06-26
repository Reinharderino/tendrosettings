import subprocess
from typing import Any, Callable

from ajustes.core.errors import CredentialError
from ajustes.core.gpg import GpgKey, parse_secret_keys_colons


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class GpgBridge:
    """Lista claves GPG secretas, exporta la pública y genera pares nuevos."""

    def __init__(self, run: Callable[[list[str]], Any] = _run_captured):
        self._run = run

    def _exec(self, args: list[str], what: str) -> Any:
        try:
            result = self._run(args)
        except FileNotFoundError as error:
            raise CredentialError("gpg no encontrado.") from error
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise CredentialError(f"{what} falló (código {result.returncode}): {snippet!r}")
        return result

    def list_keys(self) -> list[GpgKey]:
        result = self._exec(["gpg", "--list-secret-keys", "--with-colons"], "gpg list")
        return parse_secret_keys_colons(result.stdout or "")

    def export_public(self, keyid: str) -> str:
        return self._exec(["gpg", "--armor", "--export", keyid], "gpg export").stdout or ""

    def generate(self, name: str, email: str) -> None:
        """Genera un par ed25519 (cert+sign, sin caducidad). Puede pedir passphrase (pinentry)."""
        self._exec(
            ["gpg", "--batch", "--quick-generate-key", f"{name} <{email}>",
             "ed25519", "cert,sign", "0"],
            "gpg generate",
        )
