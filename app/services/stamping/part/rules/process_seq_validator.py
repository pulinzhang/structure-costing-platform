"""同一零件下工序号不得重复（工艺确认表 / 模具布点）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessSeqOccurrence:
    part_number: str
    process_seq: str
    excel_row: int | None = None


@dataclass(frozen=True, slots=True)
class DuplicateProcessSeqIssue:
    part_number: str
    process_seq: str
    count: int
    excel_rows: tuple[int, ...]


def find_duplicate_process_seqs(
    items: Sequence[ProcessSeqOccurrence],
) -> list[DuplicateProcessSeqIssue]:
    buckets: dict[tuple[str, str], list[int]] = {}
    for item in items:
        part_number = (item.part_number or "").strip()
        process_seq = (item.process_seq or "").strip()
        if not part_number or not process_seq:
            continue
        key = (part_number, process_seq)
        buckets.setdefault(key, [])
        row = item.excel_row
        buckets[key].append(int(row) if row is not None else 0)

    issues: list[DuplicateProcessSeqIssue] = []
    for (part_number, process_seq), rows in buckets.items():
        if len(rows) < 2:
            continue
        excel_rows = tuple(row for row in rows if row > 0)
        issues.append(
            DuplicateProcessSeqIssue(
                part_number=part_number,
                process_seq=process_seq,
                count=len(rows),
                excel_rows=excel_rows,
            )
        )
    issues.sort(key=lambda issue: (issue.part_number, issue.process_seq))
    return issues


def format_duplicate_process_seq_issues(
    issues: list[DuplicateProcessSeqIssue],
    *,
    source_name: str = "工艺确认表",
    limit: int = 30,
) -> str:
    if not issues:
        return ""
    lines = [
        f"上传失败：同一零件的工序号不能重复，请改{source_name}后重传。" f"共 {len(issues)} 处："
    ]
    for issue in issues[:limit]:
        row_bit = ""
        if issue.excel_rows:
            joined_rows = "、".join(str(row) for row in issue.excel_rows)
            row_bit = f"，Excel 第 {joined_rows} 行"
        lines.append(
            f"零件 {issue.part_number} 工序 {issue.process_seq} " f"出现 {issue.count} 次{row_bit}"
        )
    extra = len(issues) - limit
    if extra > 0:
        lines.append(f"另有 {extra} 处未列出")
    return "\n".join(lines)
