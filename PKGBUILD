# Maintainer: tendro
pkgname=tendrosettings
pkgver=0.1.0
pkgrel=1
pkgdesc="TendroSettings — centro de ajustes del sistema para Hyprland/CachyOS"
arch=('any')
url="https://github.com/Reinharderino/tendrosettings"
license=('MIT')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'libsecret'
)
optdepends=(
    'snapper: gestión de snapshots Btrfs'
    'grub: edición de flags del kernel y dualboot'
    'efibootmgr: gestión de arranque UEFI (dualboot)'
    'p11-kit: gestión de certificados CA (TLS)'
    'gnupg: gestión de claves GPG'
    'openssh: gestión de claves SSH'
    'polkit: autenticación para operaciones privilegiadas'
    'hyprland: integración con el loader Lua de la sesión'
)
makedepends=('python-build' 'python-installer' 'python-setuptools' 'python-wheel')
source=()  # build local: ejecutar makepkg desde el repo

build() {
    cd "$startdir"
    python -m build --wheel --no-isolation
}

package() {
    cd "$startdir"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Lanzador .desktop
    install -Dm644 data/dev.tendro.TendroSettings.desktop \
        "$pkgdir/usr/share/applications/dev.tendro.TendroSettings.desktop"

    # Loader Lua de Hyprland (lo enlaza el usuario a ~/.config/hypr/settings/init.lua)
    install -Dm644 lua/settings/init.lua \
        "$pkgdir/usr/share/tendrosettings/lua/settings/init.lua"
}
