"""模具布点对照冲压工艺：零件号、工序、有尺寸时的模具编号。"""

from app.services.stamping.die.die_number_resolver import (
    DieLayoutCheckRow,
    StampingProcessTrace,
    format_die_layout_issues,
    resolve_unique_die_number,
    validate_die_layout,
)


def _trace(
    part_number: str,
    process_seq: str,
    *,
    die_number: str | None = None,
    excel_filename: str = "常庆T13J工艺确认表.xlsx",
    stamping_supplier: str | None = "安庆常庆汽车部件有限公司",
    version: str | None = None,
) -> StampingProcessTrace:
    return StampingProcessTrace(
        part_number=part_number,
        process_seq=process_seq,
        die_number=die_number,
        excel_filename=excel_filename,
        stamping_supplier=stamping_supplier,
        version=version,
    )


def test_unique_die_number() -> None:
    number, conflict = resolve_unique_die_number({"T13J-OP05-001"})
    assert number == "T13J-OP05-001"
    assert conflict == ()


def test_missing_die_number() -> None:
    number, conflict = resolve_unique_die_number(set())
    assert number is None
    assert conflict == ()


def test_conflict_die_number() -> None:
    number, conflict = resolve_unique_die_number({"A-1", "B-1"})
    assert number is None
    assert conflict == ("A-1", "B-1")


def test_validate_copies_unique_number_when_sized() -> None:
    resolved, issues = validate_die_layout(
        [DieLayoutCheckRow("502007709AA", "OP05", True)],
        [_trace("502007709AA", "OP05", die_number="N1")],
    )
    assert issues == []
    assert resolved[("502007709AA", "OP05")] == "N1"


def test_validate_empty_number_ok_without_size() -> None:
    resolved, issues = validate_die_layout(
        [DieLayoutCheckRow("502007810AA", "OP05", False)],
        [_trace("502007810AA", "OP05")],
    )
    assert issues == []
    assert resolved == {}


def test_validate_missing_part() -> None:
    resolved, issues = validate_die_layout(
        [DieLayoutCheckRow("UNKNOWN", "OP05", True)],
        [_trace("502007709AA", "OP05", die_number="N1")],
    )
    assert resolved == {}
    assert len(issues) == 1
    assert issues[0].kind == "part_missing"
    message = format_die_layout_issues(issues)
    assert "找不到零件号 UNKNOWN" in message
    assert "工艺库中没有" in message
    assert "请先核对该基地+项目的冲压工艺确认表" in message


def test_conflict_message_does_not_ask_to_upload_process_file() -> None:
    _, issues = validate_die_layout(
        [DieLayoutCheckRow("502007733AA", "OP05", True)],
        [
            _trace(
                "502007733AA",
                "OP05",
                die_number="N2",
                excel_filename="全鑫.xlsx",
                stamping_supplier="全鑫",
            ),
            _trace(
                "502007733AA",
                "OP05",
                die_number="N3",
                excel_filename="振华.xlsx",
                stamping_supplier="振华",
            ),
        ],
    )
    message = format_die_layout_issues(issues)
    assert "编号不一致（N2、N3）" in message
    assert "请先核对该基地+项目的冲压工艺确认表" not in message
    assert message.startswith("核对失败。")


def test_validate_missing_process_shows_excel_filename() -> None:
    resolved, issues = validate_die_layout(
        [
            DieLayoutCheckRow("502007709AA", "OP99", True),
            DieLayoutCheckRow("502007709AA", "OP50", False),
        ],
        [_trace("502007709AA", "OP05", die_number="N1")],
    )
    assert resolved == {}
    assert len(issues) == 2
    assert all(item.kind == "process_missing" for item in issues)
    message = format_die_layout_issues(issues)
    assert "找不到工序 OP99、OP50" in message
    assert "请先核对该基地+项目的冲压工艺确认表" in message
    assert "常庆T13J工艺确认表.xlsx" in message
    assert "安庆常庆汽车部件有限公司" in message


def test_validate_sized_row_requires_unique_number() -> None:
    resolved, issues = validate_die_layout(
        [
            DieLayoutCheckRow("502007733AA", "OP05", True),
            DieLayoutCheckRow("502007810AA", "OP05", True),
        ],
        [
            _trace(
                "502007733AA",
                "OP05",
                die_number="N2",
                excel_filename="全鑫T13J工艺确认表.xlsx",
                stamping_supplier="全鑫",
                version="V0-01",
            ),
            _trace(
                "502007733AA",
                "OP05",
                die_number="N3",
                excel_filename="振华T13J工艺确认表.xlsx",
                stamping_supplier="振华",
                version="V0-01",
            ),
            _trace(
                "502007810AA",
                "OP05",
                excel_filename="贝奇T13J工艺确认表.xlsx",
                stamping_supplier="贝奇",
            ),
        ],
    )
    assert resolved == {}
    kinds = {item.part_number: item.kind for item in issues}
    assert kinds["502007733AA"] == "die_number_conflict"
    assert kinds["502007810AA"] == "die_number_missing"
    message = format_die_layout_issues(issues)
    assert "编号不一致（N2、N3）" in message
    assert "N2 ← 全鑫T13J工艺确认表.xlsx（全鑫，版本 V0-01）" in message
    assert "N3 ← 振华T13J工艺确认表.xlsx（振华，版本 V0-01）" in message
    assert "贝奇T13J工艺确认表.xlsx（贝奇）" in message


def test_validate_dedupes_part_missing() -> None:
    _, issues = validate_die_layout(
        [
            DieLayoutCheckRow("UNKNOWN", "OP05", True),
            DieLayoutCheckRow("UNKNOWN", "OP10", False),
        ],
        [],
    )
    assert len(issues) == 1
    assert issues[0].kind == "part_missing"
