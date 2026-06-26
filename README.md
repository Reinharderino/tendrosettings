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
