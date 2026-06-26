import gi

gi.require_version("Secret", "1")
from gi.repository import GLib, Secret  # noqa: E402

from ajustes.config import APP_ID  # noqa: E402
from ajustes.core.errors import CredentialError  # noqa: E402

APP_SCHEMA_NAME = APP_ID


class SecretItem:
    """Un ítem del Secret Service: metadatos + referencia al objeto GI (para revelar/borrar)."""

    def __init__(self, label: str, attributes: dict[str, str], collection: str, ref):
        self.label = label
        self.attributes = attributes
        self.collection = collection
        self._ref = ref


class SecretServiceBridge:
    """Gestiona el Secret Service (gnome-keyring) vía libsecret: listar, revelar
    bajo demanda, borrar y añadir. Los valores nunca se cargan al listar."""

    def _service(self):
        try:
            return Secret.Service.get_sync(Secret.ServiceFlags.LOAD_COLLECTIONS, None)
        except GLib.Error as error:
            raise CredentialError(f"No se pudo abrir el llavero: {error.message}") from error

    def list_items(self) -> list[SecretItem]:
        service = self._service()
        items: list[SecretItem] = []
        try:
            for collection in service.get_collections():
                collection.load_items_sync(None)
                coll_label = collection.get_label()
                for ref in collection.get_items():
                    items.append(SecretItem(
                        label=ref.get_label(),
                        attributes=dict(ref.get_attributes()),
                        collection=coll_label,
                        ref=ref,
                    ))
        except GLib.Error as error:
            raise CredentialError(f"Error al listar credenciales: {error.message}") from error
        return items

    def reveal(self, item: SecretItem) -> str:
        try:
            item._ref.load_secret_sync(None)
            value = item._ref.get_secret()
        except GLib.Error as error:
            raise CredentialError(f"No se pudo revelar el secreto: {error.message}") from error
        if value is None:
            return ""
        text = value.get_text()
        return text if text is not None else "(secreto binario)"

    def delete(self, item: SecretItem) -> None:
        try:
            item._ref.delete_sync(None)
        except GLib.Error as error:
            raise CredentialError(f"No se pudo borrar: {error.message}") from error

    def add(self, label: str, attributes: dict[str, str], secret: str) -> None:
        attrs = {str(k): str(v) for k, v in attributes.items()} or {"label": label}
        schema = Secret.Schema.new(
            APP_SCHEMA_NAME, Secret.SchemaFlags.NONE,
            {name: Secret.SchemaAttributeType.STRING for name in attrs},
        )
        try:
            Secret.password_store_sync(
                schema, attrs, Secret.COLLECTION_DEFAULT, label, secret, None,
            )
        except GLib.Error as error:
            raise CredentialError(f"No se pudo guardar: {error.message}") from error
