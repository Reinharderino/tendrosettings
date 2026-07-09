from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceSpec:
    number: int
    monitor: str = ""
    persistent: bool = False

    def to_dict(self) -> dict:
        return {
            "number": self.number,
            "monitor": self.monitor,
            "persistent": self.persistent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceSpec":
        number = int(data.get("number", 1))
        number = max(1, min(10, number))
        return cls(
            number=number,
            monitor=str(data.get("monitor", "")),
            persistent=bool(data.get("persistent", False)),
        )


@dataclass(frozen=True)
class WorkspaceSettings:
    workspaces: tuple[WorkspaceSpec, ...]

    def to_dict(self) -> dict:
        return {"workspaces": [w.to_dict() for w in self.workspaces]}

    @classmethod
    def from_dict(cls, data: dict) -> "WorkspaceSettings":
        raw = data.get("workspaces", [])
        workspaces = tuple(
            WorkspaceSpec.from_dict(w) for w in raw if isinstance(w, dict)
        )
        return cls(workspaces=workspaces)
