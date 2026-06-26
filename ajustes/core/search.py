from dataclasses import dataclass


@dataclass(frozen=True)
class SettingEntry:
    """Un ajuste individual localizable desde el buscador del launcher."""

    label: str
    keywords: tuple[str, ...]
    module_id: str


def search_entries(entries: list[SettingEntry], query: str) -> list[SettingEntry]:
    needle = query.strip().casefold()
    if not needle:
        return list(entries)
    return [
        entry
        for entry in entries
        if needle in entry.label.casefold()
        or any(needle in keyword.casefold() for keyword in entry.keywords)
    ]
