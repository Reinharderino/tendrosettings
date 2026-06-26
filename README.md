# TendroSettings

Centro de ajustes del sistema para Hyprland/CachyOS, en GTK4 + libadwaita.

Módulos: Wallpaper, Apariencia (gaps/bordes/blur/colores, animaciones, colores de
apps KDE/GTK), Keybindings, Monitores, Snapshots (snapper), GRUB (flags del kernel),
Dualboot (UEFI + GRUB) y Credenciales (llavero/Secret Service, SSH, GPG, TLS/CA).

La configuración propia se persiste como JSON con backups en
`~/.config/hypr/settings/` y se aplica en vivo (Hyprland) o vía herramientas nativas
(`snapper`, `update-grub`, `efibootmgr`, `plasma-apply-colorscheme`, `gsettings`,
`trust`). Las operaciones privilegiadas usan `pkexec`. Todas las rutas e identidad
de la app viven centralizadas en [`ajustes/config.py`](ajustes/config.py).

## ¿Y el compositor? — pensado para Hyprland

TendroSettings está hecho **para Hyprland**, pero **nunca edita tu `hyprland.lua`**.
Escribe JSON en `~/.config/hypr/settings/` que un *loader* Lua
(`require("settings")`) lee desde tu config — separación código/datos: tu
`hyprland.lua` queda intacto.

Estos módulos **configuran el compositor (Hyprland)** y solo aplican en Hyprland:

| Módulo | Qué toca en Hyprland |
|--------|----------------------|
| **Apariencia** | `general` (gaps, bordes), `decoration` (rounding, blur), `animations`, colores de borde |
| **Keybindings** | binds (`hl.bind`) |
| **Monitores** | salida/resolución/escala/posición + energía (hypridle) |
| **Wallpaper** | hyprpaper / swww |

Estos módulos son **agnósticos al compositor** (funcionan en cualquier distro/escritorio,
no solo Hyprland): **GRUB**, **Dualboot**, **Snapshots** y **Credenciales** (más los
**Colores de apps KDE/GTK** dentro de Apariencia, que son theming de Qt/GTK, no de Hyprland).

> Si usas otro compositor (Sway, Niri…), los módulos de Hyprland no te aplicarán, pero
> los de sistema sí. El soporte para otros compositores no está implementado.

## Dependencias (sistema)

`python python-gobject gtk4 libadwaita libsecret`
y, según el módulo: `snapper grub efibootmgr p11-kit gnupg openssh polkit`.

## Instalación

### Usuario (recomendado para desarrollo)

```bash
./install.sh
```

Instala con `pipx` (o `pip --user`), registra el lanzador y enlaza el loader Lua de
Hyprland si procede.

### Paquete (Arch/CachyOS)

```bash
makepkg -si
```

## Uso

```bash
tendrosettings
```

## Desarrollo

```bash
python -m pytest        # 313 tests
python -m ajustes       # ejecutar sin instalar
```
