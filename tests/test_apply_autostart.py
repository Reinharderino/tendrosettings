import json

from ajustes.core.apply_autostart import ApplyAutostart
from ajustes.core.autostart import AutostartEntry, AutostartSettings
from ajustes.core.config_store import ConfigStore


def test_persiste_sin_reload(tmp_path):
    use_case = ApplyAutostart(store=ConfigStore(settings_dir=tmp_path / "settings"))
    settings = AutostartSettings(entries=(
        AutostartEntry(command="vesktop", enabled=True),
        AutostartEntry(command="telegram", enabled=False),
    ))

    result = use_case.execute(settings)

    assert result == settings
    saved = json.loads((tmp_path / "settings" / "autostart.json").read_text())
    assert saved["entries"][0]["command"] == "vesktop"
    assert saved["entries"][1]["enabled"] is False
