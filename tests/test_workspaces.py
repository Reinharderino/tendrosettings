from ajustes.core.workspaces import WorkspaceSpec, WorkspaceSettings


def test_spec_roundtrip():
    spec = WorkspaceSpec(number=3, monitor="DP-1", persistent=True)
    assert WorkspaceSpec.from_dict(spec.to_dict()) == spec


def test_spec_clamps_number_to_1_10():
    assert WorkspaceSpec.from_dict({"number": 0}).number == 1
    assert WorkspaceSpec.from_dict({"number": 99}).number == 10
    assert WorkspaceSpec.from_dict({"number": 5}).number == 5


def test_spec_defaults():
    spec = WorkspaceSpec.from_dict({"number": 2})
    assert spec.monitor == ""
    assert spec.persistent is False


def test_settings_roundtrip_and_filters_non_dict():
    settings = WorkspaceSettings(workspaces=(
        WorkspaceSpec(number=1, monitor="DP-1", persistent=False),
        WorkspaceSpec(number=2, monitor="", persistent=False),
    ))
    restored = WorkspaceSettings.from_dict(settings.to_dict())
    assert restored == settings
    # entradas no-dict se descartan
    assert WorkspaceSettings.from_dict({"workspaces": [1, "x", None]}).workspaces == ()
