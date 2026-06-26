from ajustes.core.snapshots import Snapshot, parse_info_xml, read_snapshots

POST_XML = """<?xml version="1.0"?>
<snapshot>
  <type>post</type>
  <num>98</num>
  <date>2026-06-25 17:29:37</date>
  <pre_num>97</pre_num>
  <description>actualización pacman</description>
  <cleanup>number</cleanup>
</snapshot>
"""

SINGLE_XML = """<?xml version="1.0"?>
<snapshot>
  <type>single</type>
  <num>50</num>
  <date>2026-06-01 10:00:00</date>
  <description>manual</description>
</snapshot>
"""


def test_parse_post_snapshot_all_fields():
    s = parse_info_xml(POST_XML)
    assert s == Snapshot(
        num=98, type="post", date="2026-06-25 17:29:37",
        description="actualización pacman", cleanup="number", pre_num=97,
    )


def test_parse_single_snapshot_no_pre_num():
    s = parse_info_xml(SINGLE_XML)
    assert s.num == 50
    assert s.type == "single"
    assert s.pre_num is None
    assert s.cleanup == ""


def test_parse_missing_num_returns_none():
    assert parse_info_xml("<snapshot><type>single</type></snapshot>") is None


def test_parse_invalid_xml_returns_none():
    assert parse_info_xml("{not xml") is None


def test_parse_missing_description_is_empty():
    xml = "<snapshot><num>1</num><type>single</type><date>x</date></snapshot>"
    assert parse_info_xml(xml).description == ""


def test_read_snapshots_sorted_desc_and_ignores_bad_dirs(tmp_path):
    (tmp_path / "98").mkdir()
    (tmp_path / "98" / "info.xml").write_text(POST_XML, encoding="utf-8")
    (tmp_path / "50").mkdir()
    (tmp_path / "50" / "info.xml").write_text(SINGLE_XML, encoding="utf-8")
    # dir numérico sin info.xml -> ignorado
    (tmp_path / "12").mkdir()
    # dir no numérico -> ignorado
    (tmp_path / "notanum").mkdir()

    snaps = read_snapshots(tmp_path)
    assert [s.num for s in snaps] == [98, 50]  # descendente


def test_read_snapshots_missing_dir_returns_empty(tmp_path):
    assert read_snapshots(tmp_path / "nope") == []
