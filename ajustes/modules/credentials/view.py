from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ajustes.core.errors import CredentialError  # noqa: E402
from ajustes.core.gpg_bridge import GpgBridge  # noqa: E402
from ajustes.core.secrets_bridge import SecretServiceBridge  # noqa: E402
from ajustes.core.ssh_bridge import SshBridge  # noqa: E402
from ajustes.core.tls_bridge import TlsBridge  # noqa: E402


def _clear(box: Gtk.Box) -> None:
    child = box.get_first_child()
    while child is not None:
        box.remove(child)
        child = box.get_first_child()


def _epoch_str(epoch: int | None) -> str:
    if not epoch:
        return "—"
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d")


class CredentialsPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Credenciales")
        self._secrets = SecretServiceBridge()
        self._ssh = SshBridge()
        self._gpg = GpgBridge()
        self._tls = TlsBridge()
        self.set_child(self._build())
        self._refresh_secrets()
        self._refresh_ssh()
        self._refresh_gpg()
        self._refresh_tls()

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self._stack = Adw.ViewStack()
        switcher = Adw.ViewSwitcher(stack=self._stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        toolbar_view.add_top_bar(header)

        self._secrets_box = self._tab_box()
        self._ssh_box = self._tab_box()
        self._gpg_box = self._tab_box()
        self._tls_box = self._tab_box()

        self._stack.add_titled_with_icon(
            self._scroll(self._secrets_box), "secrets", "Credenciales", "dialog-password-symbolic")
        self._stack.add_titled_with_icon(
            self._scroll(self._ssh_box), "ssh", "SSH", "network-server-symbolic")
        self._stack.add_titled_with_icon(
            self._scroll(self._gpg_box), "gpg", "GPG", "application-certificate-symbolic")
        self._stack.add_titled_with_icon(
            self._scroll(self._tls_box), "tls", "TLS / CA", "security-high-symbolic")

        toolbar_view.set_content(self._stack)
        return toolbar_view

    @staticmethod
    def _tab_box() -> Gtk.Box:
        return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

    @staticmethod
    def _scroll(child: Gtk.Widget) -> Gtk.ScrolledWindow:
        return Gtk.ScrolledWindow(child=child, vexpand=True)

    @staticmethod
    def _error_row(message: str) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup()
        group.add(Adw.ActionRow(title="No disponible", subtitle=message))
        return group

    def _toast(self, message: str):
        root = self.get_root()
        if root and hasattr(root, "add_toast"):
            root.add_toast(Adw.Toast(title=message))

    # ===================== SECRET SERVICE =====================

    def _refresh_secrets(self):
        _clear(self._secrets_box)
        add_group = Adw.PreferencesGroup()
        add_btn = Gtk.Button(label="Añadir credencial", css_classes=["suggested-action"],
                             valign=Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add_secret)
        add_row = Adw.ActionRow(title="Nueva credencial en el llavero")
        add_row.add_suffix(add_btn)
        add_group.add(add_row)
        self._secrets_box.append(add_group)

        try:
            items = self._secrets.list_items()
        except CredentialError as exc:
            self._secrets_box.append(self._error_row(str(exc)))
            return

        group = Adw.PreferencesGroup(title=f"Credenciales del llavero ({len(items)})")
        for item in items:
            attrs = ", ".join(f"{k}={v}" for k, v in list(item.attributes.items())[:3]
                              if k != "xdg:schema")
            row = Adw.ActionRow(title=item.label or "(sin etiqueta)",
                                subtitle=f"[{item.collection}] {attrs}")
            reveal = Gtk.Button(icon_name="view-reveal-symbolic", valign=Gtk.Align.CENTER,
                                tooltip_text="Revelar")
            reveal.connect("clicked", self._on_reveal, item)
            delete = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["destructive-action"], tooltip_text="Borrar")
            delete.connect("clicked", self._on_delete_secret, item)
            row.add_suffix(reveal)
            row.add_suffix(delete)
            group.add(row)
        self._secrets_box.append(group)

    def _on_reveal(self, _btn, item):
        try:
            value = self._secrets.reveal(item)
        except CredentialError as exc:
            self._toast(str(exc))
            return
        dialog = Adw.AlertDialog(heading=item.label or "Secreto", body="")
        entry = Gtk.Label(label=value or "(vacío)", selectable=True, wrap=True,
                          css_classes=["monospace"], margin_top=6)
        dialog.set_extra_child(entry)
        dialog.add_response("close", "Cerrar")
        dialog.present(self)

    def _on_delete_secret(self, _btn, item):
        dialog = Adw.AlertDialog(
            heading="Borrar credencial",
            body=f"Se borrará «{item.label}» del llavero. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Borrar")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_secret_confirm, item)
        dialog.present(self)

    def _on_delete_secret_confirm(self, _dialog, response, item):
        if response != "delete":
            return
        try:
            self._secrets.delete(item)
        except CredentialError as exc:
            self._toast(str(exc))
            return
        self._refresh_secrets()

    def _on_add_secret(self, _btn):
        dialog = Adw.AlertDialog(heading="Añadir credencial", body="")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label_row = Adw.EntryRow(title="Etiqueta")
        attr_row = Adw.EntryRow(title="Atributos (clave=valor,clave=valor)")
        secret_row = Adw.PasswordEntryRow(title="Secreto")
        for r in (label_row, attr_row, secret_row):
            box.append(r)
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("save", "Guardar")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_add_secret_confirm, label_row, attr_row, secret_row)
        dialog.present(self)

    def _on_add_secret_confirm(self, _dialog, response, label_row, attr_row, secret_row):
        if response != "save":
            return
        label = label_row.get_text().strip()
        attrs = {}
        for pair in attr_row.get_text().split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                attrs[k.strip()] = v.strip()
        try:
            self._secrets.add(label or "credencial", attrs, secret_row.get_text())
        except CredentialError as exc:
            self._toast(str(exc))
            return
        self._refresh_secrets()

    # ===================== SSH =====================

    def _refresh_ssh(self):
        _clear(self._ssh_box)
        try:
            keys = self._ssh.list_keys()
        except CredentialError as exc:
            self._ssh_box.append(self._error_row(str(exc)))
            return
        if not keys:
            self._ssh_box.append(self._error_row("No se encontraron claves en ~/.ssh."))
            return
        group = Adw.PreferencesGroup(title="Claves SSH (~/.ssh)",
                                     description="Carga/descarga del agente para usarlas con Git.")
        for key in keys:
            name = Path(key.path).name
            estado = "● en el agente" if key.loaded else "○ no cargada"
            row = Adw.ActionRow(
                title=f"{name}  ·  {key.type} {key.bits}",
                subtitle=f"{key.fingerprint}  «{key.comment}»  —  {estado}",
            )
            btn = Gtk.Button(
                label="Quitar del agente" if key.loaded else "Cargar en agente",
                valign=Gtk.Align.CENTER,
            )
            btn.connect("clicked", self._on_toggle_agent, key)
            row.add_suffix(btn)
            group.add(row)
        self._ssh_box.append(group)

    def _on_toggle_agent(self, _btn, key):
        try:
            if key.loaded:
                self._ssh.remove_from_agent(key.path)
            else:
                self._ssh.add_to_agent(key.path)
        except CredentialError as exc:
            self._toast(str(exc))
        self._refresh_ssh()

    # ===================== GPG =====================

    def _refresh_gpg(self):
        _clear(self._gpg_box)
        gen_group = Adw.PreferencesGroup()
        gen_btn = Gtk.Button(label="Generar par GPG", css_classes=["suggested-action"],
                             valign=Gtk.Align.CENTER)
        gen_btn.connect("clicked", self._on_generate_gpg)
        gen_row = Adw.ActionRow(title="Nuevo par de claves (ed25519)")
        gen_row.add_suffix(gen_btn)
        gen_group.add(gen_row)
        self._gpg_box.append(gen_group)

        try:
            keys = self._gpg.list_keys()
        except CredentialError as exc:
            self._gpg_box.append(self._error_row(str(exc)))
            return
        if not keys:
            self._gpg_box.append(self._error_row("No hay claves GPG secretas."))
            return
        group = Adw.PreferencesGroup(title=f"Claves GPG ({len(keys)})")
        for key in keys:
            row = Adw.ActionRow(
                title=key.uid or key.keyid,
                subtitle=f"{key.keyid} · creada {_epoch_str(key.created)} · "
                         f"caduca {_epoch_str(key.expires)}",
            )
            export = Gtk.Button(label="Exportar pública", valign=Gtk.Align.CENTER)
            export.connect("clicked", self._on_export_gpg, key)
            row.add_suffix(export)
            group.add(row)
        self._gpg_box.append(group)

    def _on_generate_gpg(self, _btn):
        dialog = Adw.AlertDialog(heading="Generar par GPG", body="")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        name_row = Adw.EntryRow(title="Nombre")
        email_row = Adw.EntryRow(title="Email")
        box.append(name_row)
        box.append(email_row)
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("gen", "Generar")
        dialog.set_response_appearance("gen", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_generate_gpg_confirm, name_row, email_row)
        dialog.present(self)

    def _on_generate_gpg_confirm(self, _dialog, response, name_row, email_row):
        if response != "gen":
            return
        try:
            self._gpg.generate(name_row.get_text().strip(), email_row.get_text().strip())
        except CredentialError as exc:
            self._toast(str(exc))
            return
        self._refresh_gpg()

    def _on_export_gpg(self, _btn, key):
        try:
            armored = self._gpg.export_public(key.keyid)
        except CredentialError as exc:
            self._toast(str(exc))
            return
        dialog = Adw.AlertDialog(heading=f"Clave pública {key.keyid}", body="")
        label = Gtk.Label(label=armored, selectable=True, wrap=True, css_classes=["monospace"])
        dialog.set_extra_child(Gtk.ScrolledWindow(child=label, min_content_height=240))
        dialog.add_response("close", "Cerrar")
        dialog.present(self)

    # ===================== TLS / CA =====================

    def _refresh_tls(self):
        _clear(self._tls_box)
        add_group = Adw.PreferencesGroup()
        add_btn = Gtk.Button(label="Añadir CA…", css_classes=["suggested-action"],
                             valign=Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add_ca)
        add_row = Adw.ActionRow(title="Confiar en un certificado CA (.crt/.pem)")
        add_row.add_suffix(add_btn)
        add_group.add(add_row)
        self._tls_box.append(add_group)

        try:
            cas = self._tls.list_cas()
        except CredentialError as exc:
            self._tls_box.append(self._error_row(str(exc)))
            return
        group = Adw.PreferencesGroup(title=f"Anclas de confianza CA ({len(cas)})")
        for ca in cas:
            group.add(Adw.ActionRow(title=ca.label, subtitle=f"{ca.trust} · {ca.category}"))
        self._tls_box.append(group)

    def _on_add_ca(self, _btn):
        dialog = Gtk.FileDialog(title="Selecciona un certificado CA")
        dialog.open(self.get_root(), None, self._on_ca_chosen)

    def _on_ca_chosen(self, dialog, result):
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        if gfile is None:
            return
        try:
            self._tls.add_anchor(gfile.get_path())
        except CredentialError as exc:
            self._toast(str(exc))
            return
        self._refresh_tls()
