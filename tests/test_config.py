from pathlib import Path

from ajustes import config


def test_app_identity():
    assert config.APP_NAME == "TendroSettings"
    assert config.APP_ID == "dev.tendro.TendroSettings"


def test_settings_paths_consistent():
    assert config.SETTINGS_DIR.name == "settings"
    assert config.BACKUPS_DIR.parent == config.SETTINGS_DIR
    assert config.BACKUPS_DIR.name == ".backups"


def test_system_paths():
    assert config.DEFAULT_GRUB == Path("/etc/default/grub")
    assert config.SNAPSHOTS_DIR == Path("/.snapshots")
    assert config.SSH_DIR == config.HOME / ".ssh"


def test_paths_are_path_objects():
    for value in (config.SETTINGS_DIR, config.HYPRIDLE_CONF, config.SCHEMES_DIR,
                  config.KDEGLOBALS, config.ANIMATED_WALLPAPER_SCRIPT):
        assert isinstance(value, Path)
