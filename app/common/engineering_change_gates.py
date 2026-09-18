"""工程变更门禁与拒收文案常量（供 bom / 拆解 / 引擎 / 合册共用）。"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.common.period import is_in_period, period
from app.common.timezone import now

# --- 三条现网门禁 ---
EC_GATE_FULL_GENERATE = "设变后请走工程变更重传，勿整包生成"
EC_GATE_ENGINE_BREAKDOWN = "缺新树拆解，请工程变更重传"


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


# --- 合册校验拒收 ---
EC_CHANGE_ORDER_ROW_COUNT = "工程变更单至少一行"
EC_CHANGE_ORDER_TYPE_INVALID = "变更类型只准四句：完成停止、改图、增加零件、此件不装"
EC_CHANGE_ORDER_COLUMNS = "工程变更单十列填法不符合该变更类型"
EC_EFFECTIVE_MISMATCH = "生效年月与上传页不一致"
EC_PROJECT_MISMATCH = "工程变更单项目与上传页 / 投产清单不一致"
EC_CUSTOMER_MISMATCH = "顾客与投产清单头不一致"
EC_BEFORE_ASSEMBLY_INVALID = "变更前总成无效或不存在/已失效"
EC_AFTER_ASSEMBLY_EXISTS = "变更后总成已存在"
EC_AFTER_ASSEMBLY_BUSY = "同一变更后总成正在导入"
EC_SEQ_MISMATCH = "材料清单序号与投产序号不符"
EC_BOM_NEW_ROOT = "材料清单新总成数量或号与工程变更单不符"
EC_QTY_CHANGED = "用量与变更前总成不一致（工程变更不改用量）"
EC_NOT_INSTALL_SIGNAL = "此件不装必须用量 0 且备注含「此件不装」"
EC_ADD_VS_REVISE = "改图变更前零件空，或增加零件把新号写成总成"
EC_PROCESS_MISSING_NEW = "材料清单换号/新加且旧号有工艺，工艺表缺对应新号"
EC_PROCESS_EXTRA_NEW = "工艺表出现材料清单没有的新号"
EC_PROCESS_SHARED_OLD = "旧号仍挂其它有效总成，不能按改图停掉"
EC_SHEET_REQUIRED = "缺工程变更单 / 车身件材料清单 / 冲压工艺确认表"
EC_EFFECTIVE_TOO_EARLY = "生效年月必须晚于旧总成生效月"
EC_ROLLBACK_BLOCKED = "其后还有未回滚的变更，或对象已审未反审，不能删本次"
EC_INTERNAL_REQUIRED = "交货总成、分总成必须有内部号"
EC_ASSEMBLY_SKETCH_REQUIRED = "交货总成必须有总成图"
EC_PART_NOT_ON_TREE = "变更前零件不在该交货总成上，或层级不一致"
EC_REVISE_FILE_CHAIN = "改图必须在材料清单写出变更后零件及中间分总成新号"
EC_NOT_INSTALL_CHILDREN = "中间层此件不装时，下级必须同样标记"
EC_ADD_ALREADY_ON_TREE = "增加零件不得已装在变更前总成上"

# --- 变更类型（对人可见） ---
CHANGE_TYPE_STOP = "完成停止"
CHANGE_TYPE_REVISE = "改图"
CHANGE_TYPE_ADD_PART = "增加零件"
CHANGE_TYPE_NOT_INSTALL = "此件不装"

CHANGE_TYPES = frozenset(
    {
        CHANGE_TYPE_STOP,
        CHANGE_TYPE_REVISE,
        CHANGE_TYPE_ADD_PART,
        CHANGE_TYPE_NOT_INSTALL,
    }
)

PART_LEVEL_ASSEMBLY = "总成"
PART_LEVEL_L1 = "一级"
PART_LEVEL_L2 = "二级"

PART_LEVELS = frozenset({PART_LEVEL_ASSEMBLY, PART_LEVEL_L1, PART_LEVEL_L2})

NOT_INSTALL_REMARK = "此件不装"


def is_not_install_row(qty: object | None, remark: str | None) -> bool:
    """
    此件不装：用量=0 且备注含「此件不装」。单边拒收。

    设计部 Excel 习惯用量写 0 表示「本总成不再装」；仅 0 也可能是漏填。
    备注固定句防呆，避免把「暂定 0」误删出树。
    """
    from app.exceptions.base import BusinessException

    has_zero = qty is not None and Decimal(str(qty)) == 0
    has_signal = NOT_INSTALL_REMARK in (remark or "")
    if has_zero and has_signal:
        return True
    if has_zero and not has_signal:
        raise BusinessException(EC_NOT_INSTALL_SIGNAL)
    if has_signal and not has_zero:
        raise BusinessException(EC_NOT_INSTALL_SIGNAL)
    return False


# --- effect_kind ---
EFFECT_ASSEMBLY_L0 = "assembly_l0"
EFFECT_PROCESS_PART = "process_part"
EFFECT_DIE_PART = "die_part"
EFFECT_PROCUREMENT_OBJECT = "procurement_object"
EFFECT_WELDING_BREAKDOWN = "welding_breakdown"
EFFECT_PROCUREMENT_LIST = "procurement_list"


_SUBASSEMBLY_TRAILER_RE = re.compile(r"^(.*[A-Za-z]{2})(-\d+)$")


def _split_letter_version(part_number: str) -> tuple[str, str, str] | None:
    """茎、两位字母版本、分总成后缀（如 -1）。无字母版本则 None。"""
    trimmed = (part_number or "").strip()
    if not trimmed:
        return None
    trailer = ""
    core = trimmed
    matched = _SUBASSEMBLY_TRAILER_RE.fullmatch(trimmed)
    if matched:
        core = matched.group(1)
        trailer = matched.group(2)
    if len(core) < 3:
        return None
    suffix = core[-2:]
    if not suffix.isalpha():
        return None
    stem = core[:-2]
    if not stem:
        return None
    return stem, suffix.upper(), trailer


def letter_version_suffix(part_number: str) -> str | None:
    """两位字母版本（AA/AB）；分总成 `122AA-1` 仍认 AA。不足或非字母则 None。"""
    split = _split_letter_version(part_number)
    return None if split is None else split[1]


def letter_version_base(part_number: str) -> str | None:
    """去掉字母版本；分总成后缀留在茎上（`122AA-1` → `122-1`）。"""
    split = _split_letter_version(part_number)
    if split is None:
        return None
    stem, _, trailer = split
    return f"{stem}{trailer}"


def is_letter_version_bump(before: str, after: str) -> bool:
    """同茎且字母版本进一位（如 AA→AB；`122AA-1`→`122AB-1`）。"""
    before_split = _split_letter_version(before)
    after_split = _split_letter_version(after)
    if before_split is None or after_split is None:
        return False
    before_stem, before_suffix, before_trailer = before_split
    after_stem, after_suffix, after_trailer = after_split
    if before_stem != after_stem or before_trailer != after_trailer:
        return False
    return before_suffix < after_suffix


def find_letter_predecessor_number(candidates: Iterable[str], new_number: str) -> str | None:
    """在候选号中找同茎、字母版本低于新号的最大旧号。"""
    new_split = _split_letter_version(new_number)
    if new_split is None:
        return None
    new_stem, new_suffix, new_trailer = new_split
    matches: list[tuple[str, str]] = []
    for number in candidates:
        split = _split_letter_version(number)
        if split is None:
            continue
        stem, suffix, trailer = split
        if stem != new_stem or trailer != new_trailer or suffix >= new_suffix:
            continue
        matches.append((suffix, (number or "").strip()))
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def bump_letter_version(part_number: str) -> str:
    """字母版本进一位：AA→AB；`122AA-1`→`122AB-1`。"""
    from app.exceptions.base import BusinessException

    split = _split_letter_version(part_number)
    if split is None:
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
    stem, suffix, trailer = split
    first, second = suffix[0], suffix[1]
    if second == "Z":
        if first == "Z":
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        return f"{stem}{chr(ord(first) + 1)}A{trailer}"
    return f"{stem}{first}{chr(ord(second) + 1)}{trailer}"
