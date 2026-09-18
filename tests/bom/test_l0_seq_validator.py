"""材料清单 L0 总成序号必须从 1 连续。"""

from decimal import Decimal

from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode
from app.services.bom.l0_seq_validator import (
    L0SeqOccurrence,
    format_l0_seq_issues,
    inspect_l0_seq_nos,
    l0_seq_occurrences,
)
from app.services.bom.upload.gates.validate import require_consecutive_l0_seq_nos


def _row(part_number: str, seq_no: int, excel_row: int | None = None) -> L0SeqOccurrence:
    return L0SeqOccurrence(part_number=part_number, seq_no=seq_no, excel_row=excel_row)


def _l0(part_number: str, seq_no: int | None, *, source_row: int | None = None) -> BomParsedNode:
    return BomParsedNode(
        level=0,
        parent_index=None,
        sort_no=1,
        seq_no=seq_no,
        part_number=part_number,
        qty=Decimal("1"),
        node_role="supply",
        is_supply_unit=True,
        source_row=source_row,
    )


def _l1(part_number: str, parent_index: int) -> BomParsedNode:
    return BomParsedNode(
        level=1,
        parent_index=parent_index,
        sort_no=2,
        part_number=part_number,
        qty=Decimal("1"),
        node_role="make",
    )


def test_consecutive_one_to_n_is_ok() -> None:
    report = inspect_l0_seq_nos([_row("A", 1, 8), _row("B", 2, 12), _row("C", 3, 16)])
    assert report.has_issues() is False
    assert format_l0_seq_issues(report) == ""


def test_gap_and_duplicate_are_rejected() -> None:
    report = inspect_l0_seq_nos(
        [_row("A", 1, 8), _row("B", 2, 12), _row("C", 2, 16), _row("D", 4, 20)]
    )
    assert report.has_issues() is True
    message = format_l0_seq_issues(report)
    assert "总成序号必须从 1 连续编号" in message
    assert "序号 2 出现 2 次" in message
    assert "缺少序号 3" in message
    assert report.extra == ()


def test_zero_or_missing_seq_is_invalid() -> None:
    report = inspect_l0_seq_nos([_row("A", 0, 8), _row("B", 1, 12)])
    assert report.invalid[0].part_number == "A"
    message = format_l0_seq_issues(report)
    assert "序号无效（0）" in message
    assert "Excel 第 8 行" in message


def test_not_starting_at_one() -> None:
    report = inspect_l0_seq_nos([_row("A", 2, 8), _row("B", 3, 12)])
    assert report.missing == (1,)
    assert report.extra == (3,)


def test_l0_seq_occurrences_ignores_non_l0() -> None:
    nodes = [
        _l0("ASM-1", 1, source_row=5),
        _l1("CHILD-1", parent_index=0),
        _l0("ASM-2", None, source_row=10),
    ]
    items = l0_seq_occurrences(nodes)
    assert len(items) == 2
    assert items[0] == L0SeqOccurrence(part_number="ASM-1", seq_no=1, excel_row=5)
    assert items[1] == L0SeqOccurrence(part_number="ASM-2", seq_no=0, excel_row=10)


def test_require_consecutive_raises_on_gap() -> None:
    nodes = [
        _l0("A", 1, source_row=8),
        _l1("A-1", parent_index=0),
        _l0("B", 3, source_row=12),
    ]
    try:
        require_consecutive_l0_seq_nos(nodes)
    except BusinessException as exc:
        assert "缺少序号 2" in str(exc)
        return
    raise AssertionError("expected BusinessException")
