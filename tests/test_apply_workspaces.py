import json
from dataclasses import dataclass, field

from ajustes.core.apply_workspaces import ApplyWorkspaces
from ajustes.core.config_store import ConfigStore
from ajustes.core.workspaces import WorkspaceSettings, WorkspaceSpec


@dataclass
class FakeBridge:
    available: bool = True
    reloaded: int = 0

    def is_available(self):
        return self.available

    def reload(self):
        self.reloaded += 1


def make_use_case(tmp_path, bridge):
    return ApplyWorkspaces(
        store=ConfigStore(settings_dir=tmp_path / "settings"),
        bridge=bridge,
    )


def test_persiste_y_recarga(tmp_path):
    bridge = FakeBridge(available=True)
    use_case = make_use_case(tmp_path, bridge)
    settings = WorkspaceSettings(workspaces=(
        WorkspaceSpec(number=1, monitor="DP-1", persistent=True),
    ))

    result = use_case.execute(settings)

    assert result.applied_live is True
    assert bridge.reloaded == 1
    saved = json.loads((tmp_path / "settings" / "workspaces.json").read_text())
    assert saved["workspaces"][0]["monitor"] == "DP-1"


def test_sin_sesion_no_recarga(tmp_path):
    bridge = FakeBridge(available=False)
    use_case = make_use_case(tmp_path, bridge)

    result = use_case.execute(WorkspaceSettings(workspaces=()))

    assert result.applied_live is False
    assert bridge.reloaded == 0
