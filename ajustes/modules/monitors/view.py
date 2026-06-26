import re
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from ajustes.core.apply_monitors import ApplyMonitors  # noqa: E402
from ajustes.core.config_store import ConfigStore  # noqa: E402
from ajustes.core.errors import HyprlandUnavailableError  # noqa: E402
from ajustes.core.hyprland_bridge import HyprctlBridge  # noqa: E402
from ajustes.core.monitors import (  # noqa: E402
    MonitorSettings,
    MonitorSpec,
    PowerSettings,
    mode_string,
    parse_modes,
)

from ajustes.config import HYPRIDLE_CONF, SETTINGS_DIR  # noqa: E402

TRANSFORM_LABELS = MonitorSpec.TRANSFORM_LABELS
SCALE_MIN, SCALE_MAX, SCALE_STEP = 0.5, 3.0, 0.25


class _MonitorForm:
    """Widgets para configurar un único monitor."""

    def __init__(self, monitor_info: dict, saved_spec: MonitorSpec | None, on_change):
        self._name = monitor_info["name"]
        self._on_change = on_change
        available = monitor_info.get("availableModes", [])
        self._modes_by_res = parse_modes(available)
        self._resolutions = list(self._modes_by_res.keys())

        # --- Resolución ---
        self._res_row = Adw.ComboRow(title="Resolución")
        res_model = Gtk.StringList()
        for r in self._resolutions:
            res_model.append(r)
        self._res_row.set_model(res_model)
        self._res_row.connect("notify::selected", self._on_resolution_changed)

        # --- Tasa de refresco ---
        self._rate_row = Adw.ComboRow(title="Tasa de refresco")
        self._rate_model = Gtk.StringList()
        self._rate_row.set_model(self._rate_model)

        # --- Escala ---
        self._scale_row = Adw.SpinRow.new_with_range(SCALE_MIN, SCALE_MAX, SCALE_STEP)
        self._scale_row.set_title("Escala")
        self._scale_row.set_digits(2)

        # --- Posición ---
        self._pos_x_row = Adw.EntryRow(title="Posición X")
        self._pos_y_row = Adw.EntryRow(title="Posición Y")
        for row in (self._pos_x_row, self._pos_y_row):
            row.connect("changed", lambda _: self._on_change())

        # --- Rotación ---
        self._transform_row = Adw.ComboRow(title="Rotación")
        tr_model = Gtk.StringList()
        for label in TRANSFORM_LABELS:
            tr_model.append(label)
        self._transform_row.set_model(tr_model)

        # --- Activo ---
        self._enabled_row = Adw.SwitchRow(title="Activo")

        # Conectar señales de dirty
        self._scale_row.connect("notify::value", lambda *_: self._on_change())
        self._transform_row.connect("notify::selected", lambda *_: self._on_change())
        self._enabled_row.connect("notify::active", lambda *_: self._on_change())
        self._rate_row.connect("notify::selected", lambda *_: self._on_change())

        # Poblar con valores guardados o estado live
        self._populate(saved_spec, monitor_info)

    def _populate(self, saved: MonitorSpec | None, live: dict):
        if saved:
            mode = saved.mode
            scale = saved.scale
            x, y = saved.x, saved.y
            transform = saved.transform
            enabled = saved.enabled
        else:
            rate = live.get("refreshRate", 60.0)
            mode = mode_string(f"{live.get('width', 1920)}x{live.get('height', 1080)}", rate)
            scale = float(live.get("scale", 1.0))
            x, y = int(live.get("x", 0)), int(live.get("y", 0))
            transform = int(live.get("transform", 0))
            enabled = not live.get("disabled", False)

        m = re.match(r"^(\d+x\d+)@([\d.]+)Hz$", mode)
        if m:
            res, rate_str = m.group(1), float(m.group(2))
            if res in self._resolutions:
                self._res_row.set_selected(self._resolutions.index(res))
                self._populate_rates(res)
                rates = self._modes_by_res.get(res, [])
                if rate_str in rates:
                    self._rate_row.set_selected(rates.index(rate_str))

        self._scale_row.set_value(scale)
        self._pos_x_row.set_text(str(x))
        self._pos_y_row.set_text(str(y))
        self._transform_row.set_selected(max(0, min(7, transform)))
        self._enabled_row.set_active(enabled)

    def _populate_rates(self, resolution: str):
        rate_model = Gtk.StringList()
        for rate in self._modes_by_res.get(resolution, []):
            rate_model.append(f"{rate:.2f} Hz")
        self._rate_row.set_model(rate_model)

    def _on_resolution_changed(self, row, _pspec):
        idx = row.get_selected()
        if 0 <= idx < len(self._resolutions):
            self._populate_rates(self._resolutions[idx])
        self._on_change()

    def build_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=self._name)
        for row in (self._res_row, self._rate_row, self._scale_row,
                    self._pos_x_row, self._pos_y_row,
                    self._transform_row, self._enabled_row):
            group.add(row)
        return group

    def current_spec(self) -> MonitorSpec:
        res_idx = self._res_row.get_selected()
        res = self._resolutions[res_idx] if 0 <= res_idx < len(self._resolutions) else "1920x1080"
        rates = self._modes_by_res.get(res, [60.0])
        rate_idx = self._rate_row.get_selected()
        rate = rates[rate_idx] if 0 <= rate_idx < len(rates) else rates[0]
        try:
            x = int(self._pos_x_row.get_text())
        except ValueError:
            x = 0
        try:
            y = int(self._pos_y_row.get_text())
        except ValueError:
            y = 0
        return MonitorSpec(
            name=self._name,
            mode=mode_string(res, rate),
            scale=self._scale_row.get_value(),
            x=x,
            y=y,
            transform=self._transform_row.get_selected(),
            enabled=self._enabled_row.get_active(),
        )


class MonitorsPage(Adw.NavigationPage):
    def __init__(self):
        super().__init__(title="Monitores")
        self._store = ConfigStore(settings_dir=SETTINGS_DIR)
        self._bridge = HyprctlBridge()
        self._apply = ApplyMonitors(
            store=self._store,
            bridge=self._bridge,
            hypridle_conf_path=HYPRIDLE_CONF,
        )
        self._dirty = False
        self._forms: list[_MonitorForm] = []
        self.set_child(self._build())

    def _build(self) -> Gtk.Widget:
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        # Banner sin sesión Hyprland
        if not self._bridge.is_available():
            banner = Adw.Banner(
                title="Sin sesión Hyprland activa — los cambios se aplicarán al próximo inicio.",
                revealed=True,
            )
            box.append(banner)

        # Cargar datos
        monitors_live: list[dict] = []
        try:
            monitors_live = self._bridge.monitors_info()
        except HyprlandUnavailableError:
            pass

        saved_data = self._store.read("monitors") or {}
        try:
            saved_settings = MonitorSettings.from_dict(saved_data)
        except (ValueError, TypeError):
            saved_settings = MonitorSettings(monitors=(), power=PowerSettings())

        saved_by_name = {s.name: s for s in saved_settings.monitors}

        # Grupos por monitor
        if monitors_live:
            for info in monitors_live:
                form = _MonitorForm(info, saved_by_name.get(info["name"]), self._mark_dirty)
                self._forms.append(form)
                box.append(form.build_group())
        else:
            box.append(Adw.StatusPage(
                title="No se detectaron monitores",
                description="Abre esta página desde una sesión Hyprland activa.",
                icon_name="video-display-symbolic",
            ))

        # Grupo energía
        box.append(self._build_power_group(saved_settings.power))

        # Banner de error (se muestra al fallar el reload; ofrece restaurar backup)
        self._error_banner = Adw.Banner(
            title="", revealed=False,
            button_label="Restaurar backup",
        )
        self._error_banner.connect("button-clicked", self._on_restore_backup)
        box.append(self._error_banner)

        # Label de error de validación de energía
        self._power_error_label = Gtk.Label(
            css_classes=["error"], visible=False,
            halign=Gtk.Align.START, margin_start=12,
        )
        box.append(self._power_error_label)

        # Botón guardar
        self._save_btn = Gtk.Button(
            label="Guardar cambios",
            css_classes=["suggested-action", "pill"],
            sensitive=False,
            halign=Gtk.Align.CENTER,
            margin_top=12,
        )
        self._save_btn.connect("clicked", self._on_save_clicked)
        box.append(self._save_btn)

        scroll = Gtk.ScrolledWindow(child=box, vexpand=True)
        toolbar_view.set_content(scroll)
        return toolbar_view

    def _build_power_group(self, power: PowerSettings) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Energía")

        self._suspend_row = Adw.SpinRow.new_with_range(0, 120, 1)
        self._suspend_row.set_title("Suspender pantalla después de (min)")
        self._suspend_row.set_subtitle("0 = nunca")
        self._suspend_row.set_value(power.suspend_minutes)
        self._suspend_row.connect("notify::value", lambda *_: self._mark_dirty())

        self._off_row = Adw.SpinRow.new_with_range(0, 240, 1)
        self._off_row.set_title("Apagar sistema después de (min)")
        self._off_row.set_subtitle("0 = nunca")
        self._off_row.set_value(power.off_minutes)
        self._off_row.connect("notify::value", lambda *_: self._mark_dirty())

        group.add(self._suspend_row)
        group.add(self._off_row)
        return group

    def _mark_dirty(self):
        self._dirty = True
        self._save_btn.set_sensitive(True)

    def _current_power(self) -> PowerSettings | None:
        suspend = int(self._suspend_row.get_value())
        off = int(self._off_row.get_value())
        try:
            return PowerSettings(suspend_minutes=suspend, off_minutes=off)
        except ValueError as exc:
            self._power_error_label.set_text(str(exc))
            self._power_error_label.set_visible(True)
            return None

    def _on_restore_backup(self, _banner):
        try:
            restored = self._store.restore_latest_backup("monitors")
            if restored and self._bridge.is_available():
                self._bridge.reload()
            if not restored:
                self._error_banner.set_title("No hay backup disponible para restaurar.")
                self._error_banner.set_revealed(True)
                return
        except (OSError, HyprlandUnavailableError) as exc:
            self._error_banner.set_title(f"Error al restaurar: {exc}")
            self._error_banner.set_revealed(True)
            return
        self._error_banner.set_revealed(False)

    def _on_save_clicked(self, _btn):
        self._power_error_label.set_visible(False)
        power = self._current_power()
        if power is None:
            return

        specs = tuple(f.current_spec() for f in self._forms)
        settings = MonitorSettings(monitors=specs, power=power)

        dialog = Adw.AlertDialog(
            heading="Aplicar cambios",
            body="La pantalla puede parpadear brevemente al recargar Hyprland. ¿Continuar?",
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_confirm, settings)
        dialog.present(self)

    def _on_confirm(self, _dialog, response: str, settings: MonitorSettings):
        if response != "apply":
            return
        try:
            self._apply.execute(settings)
            self._dirty = False
            self._save_btn.set_sensitive(False)
            self._error_banner.set_revealed(False)
            toast = Adw.Toast(title="Monitores actualizados")
            root = self.get_root()
            if root and hasattr(root, "add_toast"):
                root.add_toast(toast)
        except (OSError, HyprlandUnavailableError, ValueError) as exc:
            self._error_banner.set_title(f"Error al aplicar: {exc}")
            self._error_banner.set_revealed(True)
