from ajustes.core.autostart import AutostartEntry, AutostartSettings


def test_entry_roundtrip():
    entry = AutostartEntry(command="vesktop", enabled=False)
    assert AutostartEntry.from_dict(entry.to_dict()) == entry


def test_entry_strips_command():
    assert AutostartEntry.from_dict({"command": "  telegram  "}).command == "telegram"


def test_entry_default_enabled():
    assert AutostartEntry.from_dict({"command": "x"}).enabled is True


def test_settings_discards_empty_and_non_dict():
    settings = AutostartSettings.from_dict({"entries": [
        {"command": "vesktop"},
        {"command": "   "},   # vacío tras strip → descartado
        "no-dict",            # descartado
        {"enabled": True},    # sin command → descartado
    ]})
    assert len(settings.entries) == 1
    assert settings.entries[0].command == "vesktop"
