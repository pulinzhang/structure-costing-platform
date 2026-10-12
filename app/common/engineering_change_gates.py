"""工程变更门禁与拒收文案常量（供 bom / 拆解 / 引擎 / 工程变更上传共用）。"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

from app.common.period import is_in_period, period
from app.common.timezone import now
from app.exceptions.base import BusinessException

_TNode = TypeVar("_TNode")

# --- 三条现网门禁 ---
EC_GATE_FULL_GENERATE = "设变后请走工程变更重传，勿整包生成"
EC_GATE_ENGINE_BREAKDOWN = "设变后的总成还没有拆解，请工程变更重传"
EC_GATE_ENGINE_PROCUREMENT = "设变后的总成还没有采购对象，请工程变更重传"


@dataclass(frozen=True, slots=True)
class PeriodRoot:
    """树根生失效四列；与 ORM Mapped 解耦后再进门禁。"""

    effective_year: int
    effective_month: int
    expiry_year: int | None
    expiry_month: int | None


def is_sop_alignable_root(
    root: PeriodRoot,
    *,
    sop_year: int,
    sop_month: int,
    as_of_year: int | None = None,
    as_of_month: int | None = None,
) -> bool:
    """SOP 再导可对齐：仍有效且生效月 = 项目 SOP 开始月。"""
    if period(root.effective_year, root.effective_month) != period(sop_year, sop_month):
        return False
    clock = now()
    year = as_of_year if as_of_year is not None else clock.year
    month = as_of_month if as_of_month is not None else clock.month
    return is_in_period(
        effective_year=root.effective_year,
        effective_month=root.effective_month,
        expiry_year=root.expiry_year,
        expiry_month=root.expiry_month,
        as_of_year=year,
        as_of_month=month,
    )


def snapshot_blocks_full_generate(
    roots: Sequence[PeriodRoot],
    *,
    sop_year: int,
    sop_month: int,
    as_of_year: int | None = None,
    as_of_month: int | None = None,
) -> bool:
    """门禁 2：已失效树根，或生效月 ≠ SOP 开始月 → 禁止整包 generate。"""
    clock = now()
    year = as_of_year if as_of_year is not None else clock.year
    month = as_of_month if as_of_month is not None else clock.month
    sop = period(sop_year, sop_month)
    for root in roots:
        if period(root.effective_year, root.effective_month) != sop:
            return True
        if not is_in_period(
            effective_year=root.effective_year,
            effective_month=root.effective_month,
            expiry_year=root.expiry_year,
            expiry_month=root.expiry_month,
            as_of_year=year,
            as_of_month=month,
        ):
            return True
    return False


# --- 工程变更校验拒收 ---
EC_CHANGE_ORDER_ROW_COUNT = "设计变更单至少一行"
EC_CHANGE_ORDER_TYPE_INVALID = "变更类型只准五句：完成停止、改图、增加零件、此件不装、增加分总成"
EC_CHANGE_ORDER_COLUMNS = "设计变更单这一行填法不对"
EC_CHANGE_ORDER_ASSEMBLY_REPEAT = "同一个总成写了多次"
EC_EFFECTIVE_MISMATCH = "生效年月与上传页不一致"
EC_PROJECT_MISMATCH = "一本只能一个项目号"


def quoted(value: object | None) -> str:
    """拒收文案里的格子：有字加书名号，空则写「（空）」。"""
    if value is None:
        return "（空）"
    text = str(value).strip()
    return f"「{text}」" if text else "（空）"


def unique_texts(values: Iterable[object]) -> list[str]:
    """去空去重，保持先出现的顺序。"""
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip() if value is not None else ""
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def listed(values: Iterable[object]) -> str:
    """拒收文案里的一串号，去空去重。"""
    items = unique_texts(values)
    return "、".join(items) if items else "（无）"


EC_BEFORE_ASSEMBLY_INVALID = "找不到这个变更前总成，或者这个月已经不用了"
EC_AFTER_ASSEMBLY_EXISTS = "变更后总成系统里已经有了"
EC_AFTER_ASSEMBLY_BUSY = "这个变更后总成正在导入，请等这次完成"
EC_AFTER_ASSEMBLY_IMPORTED = "这个变更后总成已经导入成功"
EC_BOM_NEW_ROOT = "材料清单里的交货总成和设计变更单对不上"
EC_QTY_CHANGED = "用量与变更前总成不一致（工程变更不改用量）"
EC_NOT_INSTALL_SIGNAL = "此件不装必须用量 0 且备注含「此件不装」"
EC_ADD_VS_REVISE = "改图漏了变更前零件，或把新零件号写成了总成"
EC_PROCESS_SUPPLIER_FULL_NAME = "冲压承制公司请写成供应商档案里的全称，简称不行"
EC_PROCESS_MISSING_NEW = "冲压工艺确认表少了这个新零件号"
EC_PROCESS_EXTRA_NEW = "冲压工艺确认表多了材料清单没有的号"
EC_PROCESS_NOT_ON_BOM = "冲压工艺确认表有、材料清单没有"
EC_AFTER_PART_NOT_ON_BOM = "设计变更单变更后零件有、材料清单没有"
EC_BOM_HEADER_VERSION_REQUIRED = "车身件材料清单表头版本必须填写"
EC_PROCESS_HEADER_VERSION_REQUIRED = "冲压工艺确认表表头版本必须填写"
EC_BOM_PROCESS_VERSION_MISMATCH = "车身件材料清单和冲压工艺确认表的版本必须写成同一个字"
EC_PROCUREMENT_LIST_REQUIRED = "请先到焊接工程生成采购对象列表"
EC_PROCUREMENT_LIST_REQUIRED_DETAIL = (
    f"{EC_PROCUREMENT_LIST_REQUIRED}。"
    "打开「焊接工程 → 采购对象」，对这个基地和项目点一次生成。"
    "没有生成过就不能传工程变更；只做完成停止也一样。系统不会替你建一份空的。"
)
EC_AFTER_ROOT_MISSING = "设变后的总成没有写进系统，整单不能导入"


def require_bom_header_version(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise BusinessException(
            f"{EC_BOM_HEADER_VERSION_REQUIRED}。"
            "请打开「车身件材料清单」，在第 2 行「版本：」后面填上，例如 EC-202607。没填就不能导入。"
        )
    return text


def require_process_header_version(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        raise BusinessException(
            f"{EC_PROCESS_HEADER_VERSION_REQUIRED}。"
            "请打开「冲压工艺确认表」，填上表头「版本」，和材料清单第 2 行写成一样。"
            "确认表可以没有零件行，版本这一格仍要填。"
        )
    return text


def require_ec_sheet_versions(*, bom_version: str | None, process_version: str | None) -> str:
    """材料清单与确认表版本必须同一非空字。给人看的拒收只写这一处。"""
    bom = require_bom_header_version(bom_version)
    process = require_process_header_version(process_version)
    if bom != process:
        raise BusinessException(
            f"{EC_BOM_PROCESS_VERSION_MISMATCH}。"
            f"材料清单写成了{quoted(bom)}，确认表写成了{quoted(process)}。"
            "请改成同一个字后再传。"
        )
    return bom


def after_assembly_missing_message(part_number: object | None) -> str:
    return (
        f"{EC_AFTER_ROOT_MISSING}。"
        f"设计变更单上的变更后总成{quoted(part_number)}对不上。"
        "请看「车身件材料清单」里有没有这个交货总成，改完再传。"
    )


def require_after_assembly_node(node: _TNode | None, *, part_number: object | None) -> _TNode:
    if node is None:
        raise BusinessException(after_assembly_missing_message(part_number))
    return node


def after_assembly_not_on_bom_message(part_number: object | None) -> str:
    return (
        f"{EC_BOM_NEW_ROOT}：变更后总成{quoted(part_number)}"
        "没有写在「车身件材料清单」里。请在材料清单写出这一号后再传。"
    )


EC_PROCESS_SHARED_OLD = "这个旧号还装在别的总成上，不能按改图停掉"
EC_SHEET_REQUIRED = "缺设计变更单 / 车身件材料清单 / 冲压工艺确认表"
EC_EFFECTIVE_TOO_EARLY = "生效年月必须晚于旧总成生效月"
EC_ROLLBACK_BLOCKED = "其后还有未回滚的变更，或对象已审未反审，不能删本次"
EC_INTERNAL_REQUIRED = "交货总成、分总成必须有内部号"
EC_ASSEMBLY_SKETCH_REQUIRED = "交货总成必须有总成图"
EC_PART_SKETCH_REQUIRED = "一级、二级零件必须有单件图示"
EC_PART_NOT_ON_TREE = "变更前零件不在这个总成上，或层级填错了"
EC_REVISE_FILE_CHAIN = "改图时材料清单要把换号后的零件一直写到总成"
EC_NOT_INSTALL_CHILDREN = "中间层此件不装时，下级必须同样标记"
EC_ADD_ALREADY_ON_TREE = "变更后零件已在变更前总成上"
EC_ADD_LEVEL1_NUMBER = "增加二级时，上级一级也要换成新号"
EC_ADD_LEVEL1_LEAF = "增加二级时，这个一级下面原来要有二级"

# --- 变更类型（对人可见） ---
CHANGE_TYPE_STOP = "完成停止"
CHANGE_TYPE_REVISE = "改图"
CHANGE_TYPE_ADD_PART = "增加零件"
CHANGE_TYPE_NOT_INSTALL = "此件不装"
CHANGE_TYPE_ADD_SUBASSEMBLY = "增加分总成"

CHANGE_TYPES = frozenset(
    {
        CHANGE_TYPE_STOP,
        CHANGE_TYPE_REVISE,
        CHANGE_TYPE_ADD_PART,
        CHANGE_TYPE_NOT_INSTALL,
        CHANGE_TYPE_ADD_SUBASSEMBLY,
    }
)

PART_LEVEL_ASSEMBLY = "总成"
PART_LEVEL_L1 = "一级"
PART_LEVEL_L2 = "二级"

PART_LEVELS = frozenset({PART_LEVEL_ASSEMBLY, PART_LEVEL_L1, PART_LEVEL_L2})
PART_LEVEL_TO_BOM_LEVEL = {
    PART_LEVEL_ASSEMBLY: 0,
    PART_LEVEL_L1: 1,
    PART_LEVEL_L2: 2,
}

NOT_INSTALL_REMARK = "此件不装"


def is_not_install_row(
    qty: object | None,
    remark: str | None,
    *,
    part_number: str | None = None,
) -> bool:
    """
    此件不装：用量=0 且备注含「此件不装」。单边拒收。

    设计部 Excel 习惯用量写 0 表示「本总成不再装」；仅 0 也可能是漏填。
    备注固定句防呆，避免把「暂定 0」误删出树。
    """
    has_zero = qty is not None and Decimal(str(qty)) == 0
    has_signal = NOT_INSTALL_REMARK in (remark or "")
    if has_zero and has_signal:
        return True
    who = f"{quoted(part_number)}，" if part_number else ""
    if has_zero and not has_signal:
        raise BusinessException(
            f"{EC_NOT_INSTALL_SIGNAL}：{who}用量是 0，备注没有「{NOT_INSTALL_REMARK}」。"
            f"请在备注写上「{NOT_INSTALL_REMARK}」。"
        )
    if has_signal and not has_zero:
        raise BusinessException(
            f"{EC_NOT_INSTALL_SIGNAL}：{who}备注有「{NOT_INSTALL_REMARK}」，用量却是 {qty}。"
            "用量必须是 0。"
        )
    return False


# --- effect_kind ---
EFFECT_ASSEMBLY_L0 = "assembly_l0"
EFFECT_PROCESS_PART = "process_part"
EFFECT_PART_MATERIAL_CHANGE = "part_material_change"
EFFECT_DIE_PART = "die_part"
EFFECT_GAUGE_FEE = "gauge_fee"
EFFECT_DIE_FEE = "die_fee"
EFFECT_PACKAGING_FEE = "packaging_fee"
EFFECT_ANNUAL_PART_PRICE = "annual_part_price"
EFFECT_PROCUREMENT_OBJECT = "procurement_object"
EFFECT_WELDING_BREAKDOWN = "welding_breakdown"
EFFECT_PROCUREMENT_LIST = "procurement_list"
