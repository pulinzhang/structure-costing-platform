"""材料清单根节点的总成分类：只认主数据里启用的分类。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.workbook_reject import format_workbook_reject
from app.exceptions.base import BusinessException
from app.parsers.bom.models import BomParsedNode
from app.services.masterdata.assembly_category.service import AssemblyCategoryService


def bind_root_assembly_categories(
    db: Session,
    nodes: list[BomParsedNode],
    *,
    required: bool,
) -> None:
    """把根上的「总成分类」收成分类 id。

    材料清单上传必须每个根都填。工程变更没写这一列时不动，种树时沿用旧根。
    """
    roots = [node for node in nodes if node.level == 0]
    if not roots:
        return
    filled = [node for node in roots if (node.assembly_category_label or "").strip()]
    if not required and not filled:
        return

    categories = AssemblyCategoryService().list_enabled(db)
    if not categories:
        raise BusinessException(
            "还没有启用的总成分类。请先到主数据 → 总成计费 → 总成分类里启用后再导入。"
        )
    by_name = {row.name: row for row in categories}
    by_code = {row.code: row for row in categories}
    allowed = "、".join(row.name for row in categories)
    problems: list[str] = []
    for node in roots:
        label = (node.assembly_category_label or "").strip()
        part = node.part_number or "（无零件号）"
        row_no = node.source_row or "?"
        if not label:
            problems.append(
                f"第 {row_no} 行总成「{part}」的「总成分类」是空的。" f"请填{allowed}中的一个。"
            )
            continue
        matched = by_name.get(label) or by_code.get(label)
        if matched is None:
            problems.append(
                f"第 {row_no} 行总成「{part}」的「总成分类」填了「{label}」，"
                f"不在启用分类里。请改成{allowed}中的一个。"
            )
            continue
        node.assembly_category_id = matched.id
    if problems:
        raise BusinessException(format_workbook_reject(problems))
