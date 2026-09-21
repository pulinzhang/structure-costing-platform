"""工艺确认表零件序号必须从 1 连续。"""

from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.services.stamping.part.rules.part_seq_validator import (
    PartSeqOccurrence,
    format_part_seq_issues,
    inspect_part_seq_nos,
    next_consecutive_seq_no,
)
from app.services.stamping.part.upload.gates.validate import require_consecutive_part_seq_nos


def _row(part_number: str, seq_no: int, excel_row: int | None = None) -> PartSeqOccurrence:
    return PartSeqOccurrence(part_number=part_number, seq_no=seq_no, excel_row=excel_row)


def test_consecutive_one_to_n_is_ok() -> None:
    report = inspect_part_seq_nos([_row("A", 1, 8), _row("B", 2, 12), _row("C", 3, 16)])
    assert report.has_issues() is False
    assert format_part_seq_issues(report) == ""


def test_gap_and_duplicate_are_rejected() -> None:
    report = inspect_part_seq_nos(
        [_row("A", 1, 8), _row("B", 2, 12), _row("C", 2, 16), _row("D", 4, 20)]
    )
    assert report.has_issues() is True
    message = format_part_seq_issues(report)
    assert "必须从 1 连续编号" in message
    assert "序号 2 出现 2 次" in message
    assert "缺少序号 3" in message
    assert report.extra == ()


def test_zero_seq_is_invalid() -> None:
    report = inspect_part_seq_nos([_row("A", 0, 8), _row("B", 1, 12)])
    assert report.invalid[0].part_number == "A"
    message = format_part_seq_issues(report)
    assert "序号无效（0）" in message
    assert "Excel 第 8 行" in message


def test_not_starting_at_one() -> None:
    report = inspect_part_seq_nos([_row("A", 2, 8), _row("B", 3, 12)])
    assert report.missing == (1,)
    assert report.extra == (3,)


def test_next_consecutive_seq_no() -> None:
    assert next_consecutive_seq_no([]) == 1
    assert next_consecutive_seq_no([1, 2, 3]) == 4
    assert next_consecutive_seq_no([1, None, 5]) == 6


def test_require_consecutive_raises_on_gap() -> None:
    parts = [
        Part(seq_no=1, part_number="A", excel_row=8),
        Part(seq_no=3, part_number="B", excel_row=12),
    ]
    try:
        require_consecutive_part_seq_nos(parts)
    except BusinessException as exc:
        assert "缺少序号 2" in str(exc)
        return
    raise AssertionError("expected BusinessException")
