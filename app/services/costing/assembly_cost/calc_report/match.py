"""计算报告核价卡筛选。"""

from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcCardTraceVO
from app.services.costing.assembly_cost.calc_report.labels import TreeRootFilter
from app.services.costing.assembly_cost.codes import part_short_code


def match_calc_report_card(
    card: AssemblyCostCalcCardTraceVO,
    *,
    keyword: str | None = None,
    status: str | None = None,
    level: int | None = None,
    tree_root: TreeRootFilter = "all",
) -> bool:
    if status and card.status != status:
        return False
    if level is not None and card.level != level:
        return False
    if tree_root == "yes" and not card.is_tree_root:
        return False
    if tree_root == "no" and card.is_tree_root:
        return False
    needle = (keyword or "").strip().lower()
    if not needle:
        return True
    hay = " ".join(
        [
            card.part_number or "",
            part_short_code(part_number=card.part_number, level=card.level),
            card.part_name or "",
            card.message or "",
            card.object_kind or "",
            *card.missing_parts,
        ]
    ).lower()
    return needle in hay
