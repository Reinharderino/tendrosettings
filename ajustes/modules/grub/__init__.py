from ajustes.core.search import SettingEntry

MODULE_ID = "grub"

ENTRIES = [
    SettingEntry(
        label="GRUB · Flags del kernel",
        keywords=("grub", "kernel", "cmdline", "flags", "boot", "arranque",
                  "parámetros", "tweaks", "mitigations", "quiet"),
        module_id=MODULE_ID,
    ),
    SettingEntry(
        label="Editar parámetros de arranque",
        keywords=("cmdline", "kernel", "grub", "boot", "quiet", "loglevel"),
        module_id=MODULE_ID,
    ),
]
