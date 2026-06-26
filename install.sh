#!/usr/bin/env bash
# Instalador de TendroSettings a nivel de usuario (sin root).
# Instala la app con pipx (o pip --user), registra el .desktop y, si existe la
# config de Hyprland, deja el loader Lua enlazado. Idempotente y no destructivo.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_SRC="$REPO_DIR/data/dev.tendro.TendroSettings.desktop"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
HYPR_SETTINGS="$HOME/.config/hypr/settings"

echo ":: Instalando TendroSettings (Python) ..."
if command -v pipx >/dev/null 2>&1; then
    pipx install --system-site-packages --force "$REPO_DIR"   # --system-site-packages: usa PyGObject del sistema
else
    echo "   pipx no encontrado; usando pip --user."
    pip install --user --force-reinstall "$REPO_DIR"
fi

echo ":: Registrando lanzador .desktop ..."
mkdir -p "$APPS_DIR"
install -m644 "$DESKTOP_SRC" "$APPS_DIR/"
update-desktop-database "$APPS_DIR" 2>/dev/null || true

# Integración Hyprland: enlaza el loader Lua si hay config de Hyprland y no está ya.
if [ -d "$HOME/.config/hypr" ]; then
    mkdir -p "$HYPR_SETTINGS"
    if [ ! -e "$HYPR_SETTINGS/init.lua" ]; then
        ln -s "$REPO_DIR/lua/settings/init.lua" "$HYPR_SETTINGS/init.lua"
        echo ":: Loader Lua enlazado en $HYPR_SETTINGS/init.lua"
    else
        echo ":: $HYPR_SETTINGS/init.lua ya existe — no se toca."
    fi
fi

echo ":: Listo. Ejecuta 'tendrosettings' o búscalo en el menú de apps."
