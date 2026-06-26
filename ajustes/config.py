"""Configuración central de TendroSettings.

Único lugar con la identidad de la app y todas las rutas del sistema que usan
los módulos. Antes estaban repetidas en cada view/bridge.
"""
import os
from pathlib import Path

# --- Identidad de la app ---
APP_ID = "dev.tendro.TendroSettings"
APP_NAME = "TendroSettings"
APP_TITLE = "TendroSettings"

HOME = Path.home()

# --- Config de Hyprland / store propio (JSON con backups) ---
HYPR_CONFIG_DIR = HOME / ".config/hypr"
# Permite override por entorno (igual que el loader Lua settings/init.lua).
SETTINGS_DIR = Path(os.environ.get("HYPR_AJUSTES_DIR", str(HYPR_CONFIG_DIR / "settings")))
BACKUPS_DIR = SETTINGS_DIR / ".backups"

HYPRIDLE_CONF = HYPR_CONFIG_DIR / "hypridle.conf"
HYPRPAPER_CONF = HYPR_CONFIG_DIR / "hyprpaper.conf"
ANIMATED_WALLPAPER_SCRIPT = HYPR_CONFIG_DIR / "scripts/wallpaper-swww.sh"

# --- Apariencia de apps (KDE/GTK) ---
SCHEMES_DIR = HOME / ".local/share/color-schemes"
KDEGLOBALS = HOME / ".config/kdeglobals"

# --- Sistema ---
SNAPSHOTS_DIR = Path("/.snapshots")
DEFAULT_GRUB = Path("/etc/default/grub")
SSH_DIR = HOME / ".ssh"
