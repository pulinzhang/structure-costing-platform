"""BOM 节点顺序：seq_no → level →（L0 零件号）→ excel_row → part_number。

改图后 AA/AB 抄同一条 SOP excel_row，L0 靠零件号分先后。
子件仍先 excel_row 再零件号。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, func
from sqlalchemy.sql.elements import ColumnElement

MISSING_SEQ_NO = 10**9


def bom_node_order_key(
    *,
    seq_no: int | None,
    level: int | None,
    excel_row: int | None,
    part_number: str | None = None,
    sort_no: int | None = None,
    node_id: int = 0,
) -> tuple[int, int, str, int, str, int, int]:
    ordered_seq_no = int(seq_no) if seq_no is not None else MISSING_SEQ_NO
    ordered_level = int(level) if level is not None else 0
    ordered_excel_row = int(excel_row) if excel_row is not None else int(sort_no or 0)
    ordered_part_number = (part_number or "").strip()
    l0_part_number = ordered_part_number if ordered_level == 0 else ""
    return (
        ordered_seq_no,
        ordered_level,
        l0_part_number,
        ordered_excel_row,
        ordered_part_number,
        int(sort_no or 0),
        int(node_id),
    )


# case() 的类型存根固定是 Case[Any]。写成 type[BomNode] 之后，返回值对不上 ColumnElement[object]，不能靠 cast 抹平。
def bom_node_sql_order(node: Any) -> tuple[ColumnElement[object], ...]:
    """与 list_by_snapshot 同一套：seq_no 槽 → level → L0 零件号 → excel_row。"""
    seq_no = node.seq_no
    level = node.level
    part_number = node.part_number
    excel_row = node.excel_row
    sort_no = node.sort_no
    node_id = node.id
    return (
        func.coalesce(seq_no, MISSING_SEQ_NO),
        level,
        case((level == 0, part_number), else_=""),
        func.coalesce(excel_row, sort_no, 0),
        part_number,
        sort_no,
        node_id,
    )


def bom_node_order_from(node: object) -> tuple[int, int, str, int, str, int, int]:
    return bom_node_order_key(
        seq_no=getattr(node, "seq_no", None),
        level=getattr(node, "level", None),
        excel_row=getattr(node, "excel_row", None),
        part_number=getattr(node, "part_number", None),
        sort_no=getattr(node, "sort_no", None),
        node_id=int(getattr(node, "id", 0) or 0),
    )
