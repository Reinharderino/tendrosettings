from dataclasses import dataclass


@dataclass(frozen=True)
class AutostartEntry:
    command: str
    enabled: bool = True

    def to_dict(self) -> dict:
        return {"command": self.command, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data: dict) -> "AutostartEntry":
        return cls(
            command=str(data.get("command", "")).strip(),
            enabled=bool(data.get("enabled", True)),
        )


@dataclass(frozen=True)
class AutostartSettings:
    entries: tuple[AutostartEntry, ...]

    def to_dict(self) -> dict:
        return {"entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, data: dict) -> "AutostartSettings":
        raw = data.get("entries", [])
        entries = tuple(
            entry
            for item in raw
            if isinstance(item, dict)
            for entry in (AutostartEntry.from_dict(item),)
            if entry.command
        )
        return cls(entries=entries)
