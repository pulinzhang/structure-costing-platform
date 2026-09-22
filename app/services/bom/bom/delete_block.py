"""删节点 / 再导 / 回滚被外键挡住之后，按实际引用拼说明。只读表名，不进删除前预检。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

_CHUNK = 500

_ASSEMBLY_PAGE = "核价 → 总成核价 → 总成核价一览"
_CHANGE_PAGE = "工程变更 → 设计变更 → 工程变更单列表"
_DIE_PAGE = "冲压工程 → 冲压模具费 → 冲压模具费列表"
_WELDING_FEE_PAGE = "焊接工程 → 焊接费 → 焊接费列表"


class BomReimportBlocked(Exception):
    """再导删子孙时外键拒绝。由上传壳回滚后再说明，不在 delete_descendants 里转业务异常。"""

    def __init__(self, node_ids: list[int], *, location: str, vehicle_model: str) -> None:
        self.node_ids = node_ids
        self.location = location
        self.vehicle_model = vehicle_model
        super().__init__("bom reimport blocked")


def is_foreign_key_error(error: BaseException) -> bool:
    detail = str(getattr(error, "orig", error))
    return "FOREIGN KEY constraint failed" in detail


def explain_bom_delete_blocked(
    db: Session,
    node_ids: list[int],
    *,
    location: str,
    vehicle_model: str,
    replacing_children: bool = False,
) -> str:
    """node_ids 必须是这次删除会带走的全部节点（点一个含子孙，整份清单含全部，再导不含总成根）。"""
    periods = _assembly_periods(db, node_ids)
    has_change_order = _exists(
        db,
        "SELECT 1 FROM engineering_change_orders WHERE before_assembly_node_id IN :ids LIMIT 1",
        node_ids,
    )
    parts: list[str] = []
    if replacing_children:
        parts.append("这次是在换总成下面的零件。")
    if periods:
        period_text = "、".join(f"{year}年{month:02d}月" for year, month in periods)
        parts.append(
            f"删不了：这些零件在以下年月还有总成核价：{period_text}。"
            f"请打开「{_ASSEMBLY_PAGE}」，逐个月选基地 {location}、项目 {vehicle_model}，用批量删除。"
            "不要只删列表上看得见的总成，财务视图不显示一级卡，批量删除会一起删掉。"
            "若提示跳过了已审核的，再对同一个月点批量反审核，然后重新批量删除。"
            "处理完所有列出的年月，再回到这里删除。"
        )
    if has_change_order:
        parts.append(
            "删不了：这些总成还在工程变更单里。"
            f"请打开「{_CHANGE_PAGE}」，找到这一本，删除并回滚。"
            "回滚完再回到这里删除。"
        )
    if len(parts) == (1 if replacing_children else 0):
        parts.append("这次没有删成。")
    return "".join(parts)


def explain_rollback_blocked(
    db: Session,
    links: list[tuple[str, int | None]],
    *,
    location: str,
    vehicle_model: str,
) -> str:
    """links 是这次要删的效果链 (effect_kind, after_id)。只写查到仍有引用的种类。"""
    from app.common.engineering_change_gates import (
        EC_ROLLBACK_REFERENCED,
        EFFECT_ASSEMBLY_L0,
        EFFECT_DIE_PART,
        EFFECT_PROCESS_PART,
        EFFECT_WELDING_BREAKDOWN,
    )

    process_ids = _after_ids(links, EFFECT_PROCESS_PART)
    die_ids = _after_ids(links, EFFECT_DIE_PART)
    breakdown_ids = _after_ids(links, EFFECT_WELDING_BREAKDOWN)
    assembly_ids: list[int] = []
    for root_id in _after_ids(links, EFFECT_ASSEMBLY_L0):
        assembly_ids.extend(_subtree_ids(db, root_id))

    from app.services.stamping.part.delete_block import explain_part_rollback_blocked

    parts: list[str] = []
    part_block = explain_part_rollback_blocked(db, process_ids)
    if part_block:
        parts.append(part_block)
    if _exists(
        db,
        "SELECT 1 FROM stamping_die_fees WHERE source_die_part_id IN :ids LIMIT 1",
        die_ids,
    ):
        parts.append(_fee_line("冲压模具费", _DIE_PAGE, location, vehicle_model))
    if _exists(
        db,
        "SELECT 1 FROM bom_welding_fees WHERE source_breakdown_node_id IN :ids LIMIT 1",
        breakdown_ids,
    ):
        parts.append(_fee_line("焊接费", _WELDING_FEE_PAGE, location, vehicle_model))
    periods = _assembly_periods(db, assembly_ids)
    if periods:
        period_text = "、".join(f"{year}年{month:02d}月" for year, month in periods)
        parts.append(
            f"回滚不了，因为这些零件在以下年月还有总成核价：{period_text}。"
            f"请打开「{_ASSEMBLY_PAGE}」，逐个月选基地 {location}、项目 {vehicle_model}，用批量删除。"
            "不要只删列表上看得见的总成，财务视图不显示一级卡，批量删除会一起删掉。"
            "若提示跳过了已审核的，再对同一个月点批量反审核，然后重新批量删除。"
            f"处理完所有列出的年月，再回到「{_CHANGE_PAGE}」重新删除这一本。"
        )
    if not parts:
        return EC_ROLLBACK_REFERENCED
    return "".join(parts)


def _fee_line(label: str, page: str, location: str, vehicle_model: str) -> str:
    return (
        f"回滚不了，因为{label}还在。"
        f"请打开「{page}」，按基地 {location}、项目 {vehicle_model} 处理完，"
        f"再回到「{_CHANGE_PAGE}」重新删除这一本。"
    )


def _after_ids(links: list[tuple[str, int | None]], kind: str) -> list[int]:
    return [after_id for effect_kind, after_id in links if effect_kind == kind and after_id]


def _assembly_periods(db: Session, node_ids: list[int]) -> list[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    for chunk in _chunks(node_ids):
        rows = _select(
            db,
            "SELECT DISTINCT year, month FROM costing_assembly_costs WHERE source_node_id IN :ids",
            chunk,
        )
        for year, month in rows:
            found.add((int(year), int(month)))
    return sorted(found)


def _subtree_ids(db: Session, root_id: int) -> list[int]:
    rows = db.execute(
        text(
            "WITH RECURSIVE tree(id) AS ("
            " SELECT id FROM bom_nodes WHERE id = :root"
            " UNION"
            " SELECT n.id FROM bom_nodes AS n JOIN tree AS t ON n.parent_id = t.id"
            ") SELECT id FROM tree"
        ),
        {"root": root_id},
    ).all()
    return [int(row[0]) for row in rows]


def _exists(db: Session, sql: str, ids: list[int]) -> bool:
    return any(_select(db, sql, chunk) for chunk in _chunks(ids))


def _select(db: Session, sql: str, ids: list[int]) -> list[tuple[Any, ...]]:
    statement = text(sql).bindparams(bindparam("ids", expanding=True))
    return [tuple(row) for row in db.execute(statement, {"ids": ids}).all()]


def _chunks(ids: list[int]) -> list[list[int]]:
    unique = list(dict.fromkeys(ids))
    return [unique[start : start + _CHUNK] for start in range(0, len(unique), _CHUNK)]
