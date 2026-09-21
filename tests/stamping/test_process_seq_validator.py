"""同一零件工序号不得重复。"""

from app.services.stamping.part.rules.process_seq_validator import (
    ProcessSeqOccurrence,
    find_duplicate_process_seqs,
    format_duplicate_process_seq_issues,
)


def _row(part_number: str, process_seq: str, excel_row: int | None = None) -> ProcessSeqOccurrence:
    return ProcessSeqOccurrence(
        part_number=part_number,
        process_seq=process_seq,
        excel_row=excel_row,
    )


def test_no_duplicate_process_seq() -> None:
    issues = find_duplicate_process_seqs(
        [
            _row("502007703AA", "OP10", 10),
            _row("502007703AA", "OP30", 12),
        ]
    )
    assert issues == []
    assert format_duplicate_process_seq_issues(issues) == ""


def test_duplicate_op30_lists_excel_rows() -> None:
    issues = find_duplicate_process_seqs(
        [
            _row("502007703AA", "OP30", 12),
            _row("502007703AA", "OP10", 11),
            _row("502007703AA", "OP30", 18),
        ]
    )
    assert len(issues) == 1
    assert issues[0].part_number == "502007703AA"
    assert issues[0].process_seq == "OP30"
    assert issues[0].count == 2
    assert issues[0].excel_rows == (12, 18)
    message = format_duplicate_process_seq_issues(issues)
    assert "请改工艺确认表后重传" in message
    assert "零件 502007703AA 工序 OP30 出现 2 次，Excel 第 12、18 行" in message
    die_message = format_duplicate_process_seq_issues(issues, source_name="模具布点清单")
    assert "请改模具布点清单后重传" in die_message


def test_duplicate_across_two_parts() -> None:
    issues = find_duplicate_process_seqs(
        [
            _row("A", "OP05", 2),
            _row("A", "OP05", 3),
            _row("B", "OP10", 4),
            _row("B", "OP10", 5),
        ]
    )
    assert len(issues) == 2
    message = format_duplicate_process_seq_issues(issues)
    assert "共 2 处" in message
    assert "零件 A 工序 OP05" in message
    assert "零件 B 工序 OP10" in message
