import subprocess
from pathlib import Path
from typing import Any, Callable

from ajustes.config import SSH_DIR
from ajustes.core.errors import CredentialError
from ajustes.core.ssh_keys import (
    SshKey,
    discover_key_paths,
    parse_agent_fingerprints,
    parse_fingerprint,
)


def _run_captured(args: list[str]) -> Any:
    return subprocess.run(args, capture_output=True, text=True)


class SshBridge:
    """Lista claves SSH (~/.ssh) y gestiona su carga en el agente."""

    def __init__(
        self,
        run: Callable[[list[str]], Any] = _run_captured,
        ssh_dir: Path | None = None,
    ):
        self._run = run
        self._ssh_dir = ssh_dir or SSH_DIR

    def list_keys(self) -> list[SshKey]:
        loaded = parse_agent_fingerprints(self._agent_output())
        keys: list[SshKey] = []
        for priv in discover_key_paths(self._ssh_dir):
            parsed = parse_fingerprint(self._fingerprint_output(str(priv) + ".pub"))
            if parsed is None:
                continue
            bits, fingerprint, comment, ktype = parsed
            keys.append(SshKey(
                path=str(priv), type=ktype, bits=bits, fingerprint=fingerprint,
                comment=comment, loaded=fingerprint in loaded,
            ))
        return keys

    def _agent_output(self) -> str:
        try:
            return self._run(["ssh-add", "-l"]).stdout or ""
        except FileNotFoundError:
            return ""

    def _fingerprint_output(self, pub_path: str) -> str:
        try:
            return self._run(["ssh-keygen", "-lf", pub_path]).stdout or ""
        except FileNotFoundError as error:
            raise CredentialError("ssh-keygen no encontrado.") from error

    def add_to_agent(self, private_path: str) -> None:
        self._ssh_add(["ssh-add", private_path])

    def remove_from_agent(self, private_path: str) -> None:
        self._ssh_add(["ssh-add", "-d", private_path])

    def _ssh_add(self, args: list[str]) -> None:
        try:
            result = self._run(args)
        except FileNotFoundError as error:
            raise CredentialError("ssh-add no encontrado.") from error
        if result.returncode != 0:
            snippet = (result.stdout or "")[:160]
            raise CredentialError(f"ssh-add falló (código {result.returncode}): {snippet!r}")
