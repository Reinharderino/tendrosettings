from ajustes.core.search import SettingEntry

MODULE_ID = "dualboot"

ENTRIES = [
    SettingEntry(
        label="Dualboot",
        keywords=("dualboot", "dual", "boot", "windows", "arranque", "uefi",
                  "efi", "bootorder", "bootnext", "sistema operativo"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Arrancar otro SO",
        keywords=("windows", "arrancar", "reiniciar", "bootnext", "dualboot"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="SO por defecto y timeout",
        keywords=("por defecto", "bootorder", "timeout", "os-prober", "grub", "dualboot"),
        module_id=MODULE_ID,
    ),
]
