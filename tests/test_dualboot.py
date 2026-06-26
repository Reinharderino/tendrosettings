from ajustes.core.dualboot import (
    BootEntry,
    EfiBootState,
    build_bootorder,
    parse_efibootmgr,
)

SAMPLE = """BootCurrent: 0001
Timeout: 1 seconds
BootOrder: 0001,0000,0005,0004,0006
Boot0000* Windows Boot Manager\tHD(2,GPT,aa57,0xfa000,0x31800)/\\EFI\\MICROSOFT\\BOOT\\BOOTMGFW.EFI
Boot0001* Garuda\tHD(2,GPT,aa57,0xfa000,0x31800)/\\EFI\\GARUDA\\GRUBX64.EFI
Boot0004* WD Green SN350 2TB\tBBS(HD,,0x0)0000424f
Boot0005* KINGSTON SA400M8480G\tBBS(HD,,0x0)0000424f
Boot0006* CT1000MX500SSD1\tBBS(HD,,0x0)0000424f
"""


def test_parse_current_order_timeout():
    state = parse_efibootmgr(SAMPLE)
    assert state.current == "0001"
    assert state.order == ("0001", "0000", "0005", "0004", "0006")
    assert state.timeout == 1
    assert state.boot_next is None


def test_parse_entries_labels_and_active():
    state = parse_efibootmgr(SAMPLE)
    by_num = {e.num: e for e in state.entries}
    assert by_num["0000"].label == "Windows Boot Manager"
    assert by_num["0001"].label == "Garuda"
    assert by_num["0000"].active is True


def test_parse_marks_current_entry():
    state = parse_efibootmgr(SAMPLE)
    by_num = {e.num: e for e in state.entries}
    assert by_num["0001"].is_current is True
    assert by_num["0000"].is_current is False


def test_parse_boot_next_when_present():
    text = SAMPLE + "BootNext: 0000\n"
    assert parse_efibootmgr(text).boot_next == "0000"


def test_parse_inactive_entry():
    text = "BootOrder: 0002\nBoot0002  Disabled Entry\tHD(1)\n"
    entry = parse_efibootmgr(text).entries[0]
    assert entry.active is False
    assert entry.label == "Disabled Entry"


def test_parse_empty_is_safe():
    state = parse_efibootmgr("")
    assert state.entries == ()
    assert state.order == ()
    assert state.current is None


# --- build_bootorder ---

def test_build_bootorder_moves_chosen_to_front():
    state = parse_efibootmgr(SAMPLE)
    assert build_bootorder(state, "0000") == ["0000", "0001", "0005", "0004", "0006"]


def test_build_bootorder_already_first_unchanged():
    state = parse_efibootmgr(SAMPLE)
    assert build_bootorder(state, "0001") == ["0001", "0000", "0005", "0004", "0006"]


def test_build_bootorder_num_not_in_order_prepended():
    state = EfiBootState(entries=(), order=("0001",), current=None, boot_next=None, timeout=5)
    assert build_bootorder(state, "0009") == ["0009", "0001"]
