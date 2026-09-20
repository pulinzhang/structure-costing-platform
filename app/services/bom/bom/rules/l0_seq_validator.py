"""材料清单 L0 总成序号：引入时必须从 1 连续编号。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.parsers.bom.models import BomParsedNode


@dataclass(frozen=True, slots=True)
class L0SeqOccurrence:
    part_number: str
    seq_no: int
    excel_row: int | None = None


@dataclass(frozen=True, slots=True)
class DuplicateL0SeqIssue:
    seq_no: int
    count: int
    part_numbers: tuple[str, ...]
    excel_rows: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class L0SeqValidation:
    invalid: tuple[L0SeqOccurrence, ...]
    duplicates: tuple[DuplicateL0SeqIssue, ...]
    missing: tuple[int, ...]
    extra: tuple[int, ...]

    def has_issues(self) -> bool:
        return bool(self.invalid or self.duplicates or self.missing or self.extra)


def inspect_l0_seq_nos(items: Sequence[L0SeqOccurrence]) -> L0SeqValidation:
    if not items:
        return L0SeqValidation(invalid=(), duplicates=(), missing=(), extra=())

    invalid = tuple(item for item in items if item.seq_no < 1)
    buckets: dict[int, list[L0SeqOccurrence]] = {}
    for item in items:
        buckets.setdefault(item.seq_no, []).append(item)
    duplicates: list[DuplicateL0SeqIssue] = []
    for seq_no, rows in sorted(buckets.items()):
        if len(rows) < 2:
            continue
        excel_rows = tuple(row.excel_row for row in rows if row.excel_row)
        duplicates.append(
            DuplicateL0SeqIssue(
                seq_no=seq_no,
                count=len(rows),
                part_numbers=tuple(row.part_number for row in rows),
                excel_rows=excel_rows,
            )
        )
    expected = set(range(1, len(items) + 1))
    actual = {item.seq_no for item in items if item.seq_no >= 1}
    missing = tuple(sorted(expected - actual))
    extra = tuple(sorted(actual - expected))
    return L0SeqValidation(
        invalid=invalid,
        duplicates=tuple(duplicates),
        missing=missing,
        extra=extra,
    )


def format_l0_seq_issues(
    report: L0SeqValidation,
    *,
    source_name: str = "材料清单",
    limit: int = 30,
) -> str:
    if not report.has_issues():
        return ""
    lines = [f"上传失败：{source_name}总成序号必须从 1 连续编号，请改表后重传。"]
    shown = 0
    for item in report.invalid:
        if shown >= limit:
            break
        row_bit = f"，Excel 第 {item.excel_row} 行" if item.excel_row else ""
        lines.append(f"总成 {item.part_number} 序号无效（{item.seq_no}）{row_bit}")
        shown += 1
    for issue in report.duplicates:
        if shown >= limit:
            break
        row_bit = ""
        if issue.excel_rows:
            joined_rows = "、".join(str(row) for row in issue.excel_rows)
            row_bit = f"，Excel 第 {joined_rows} 行"
        joined_parts = "、".join(issue.part_numbers)
        lines.append(f"序号 {issue.seq_no} 出现 {issue.count} 次（{joined_parts}）{row_bit}")
        shown += 1
    if report.missing and shown < limit:
        joined = "、".join(str(seq_no) for seq_no in report.missing[: max(limit - shown, 0)])
        lines.append(f"缺少序号 {joined}")
        shown += 1
    if report.extra and shown < limit:
        joined = "、".join(str(seq_no) for seq_no in report.extra[: max(limit - shown, 0)])
        lines.append(f"多出序号 {joined}")
        shown += 1
    leftover = (
        len(report.invalid)
        + len(report.duplicates)
        + (1 if report.missing else 0)
        + (1 if report.extra else 0)
        - shown
    )
    if leftover > 0:
        lines.append(f"另有 {leftover} 处未列出")
    return "\n".join(lines)


def l0_seq_occurrences(nodes: list[BomParsedNode]) -> list[L0SeqOccurrence]:
    """仅取 L0 总成；缺序号按 0 记入，由校验判为无效。"""
    items: list[L0SeqOccurrence] = []
    for node in nodes:
        if node.level != 0:
            continue
        part_number = (node.part_number or "").strip()
        if not part_number:
            continue
        items.append(
            L0SeqOccurrence(
                part_number=part_number,
                seq_no=int(node.seq_no) if node.seq_no is not None else 0,
                excel_row=node.source_row,
            )
        )
    return items
