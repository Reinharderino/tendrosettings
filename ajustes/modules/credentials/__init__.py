from ajustes.core.search import SettingEntry

MODULE_ID = "credentials"

ENTRIES = [
    SettingEntry(
        label="Credenciales",
        keywords=("credenciales", "wallet", "keyring", "llavero", "contraseñas",
                  "secret", "gnome-keyring", "tokens"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Claves SSH (Git)",
        keywords=("ssh", "clave", "git", "agente", "id_ed25519", "fingerprint"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Claves GPG",
        keywords=("gpg", "pgp", "firma", "firmar", "commits"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Certificados TLS / CA",
        keywords=("tls", "ssl", "certificado", "ca", "ancla", "trust"),
        module_id=MODULE_ID,
    ),
]
