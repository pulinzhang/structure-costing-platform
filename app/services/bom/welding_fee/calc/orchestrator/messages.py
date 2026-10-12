"""焊接费计算过程文案（给人看，不写字段名）。"""

from __future__ import annotations


def format_prep_opening(year: int, location: str, vehicle_model: str) -> str:
    return f"开始计算：{year}年，{location}，{vehicle_model}。"


def format_prices_loaded(price_count: int) -> str:
    return f"本年本基地有 {price_count} 条焊接单价。"


def level_label(level: int) -> str:
    if int(level) == 0:
        return "供货总成"
    if int(level) == 1:
        return "分总成"
    return "更下层零件"


def format_nodes_in_scope(node_count: int, levels: list[int]) -> str:
    kinds: list[str] = []
    ordered = sorted({int(level) for level in levels})
    if 0 in ordered:
        kinds.append(level_label(0))
    if 1 in ordered:
        kinds.append(level_label(1))
    if any(level >= 2 for level in ordered):
        kinds.append(level_label(2))
    if not kinds:
        return f"要算 {node_count} 个零件。"
    if len(kinds) == 1:
        return f"要算 {node_count} 个零件，都是{kinds[0]}。"
    return f"要算 {node_count} 个零件，包含{'、'.join(kinds)}。"


def format_persist_summary(
    created_count: int,
    updated_count: int,
    failed_count: int,
    missing_price_count: int,
    skipped_approved_count: int,
    *,
    point_at_reasons: bool = True,
) -> str:
    if created_count and updated_count:
        head = f"新写入 {created_count} 条，重算 {updated_count} 条"
    elif created_count:
        head = f"新写入焊接费 {created_count} 条"
    elif updated_count:
        head = f"重算焊接费 {updated_count} 条"
    else:
        head = "没有写入焊接费"

    notes: list[str] = []
    if failed_count:
        if point_at_reasons:
            notes.append(f"{failed_count} 条没算上，原因写在下面")
        else:
            notes.append(f"{failed_count} 条没算上")
    if missing_price_count:
        notes.append(f"{missing_price_count} 条工艺在本年单价里对不上")
    if skipped_approved_count:
        notes.append(f"{skipped_approved_count} 条已经审核过，这次没重算")
    if notes:
        return f"{head}。{'。'.join(notes)}。"
    if created_count or updated_count:
        return f"{head}。没有失败，单价都对上了。"
    return f"{head}。"


def format_missing_prices(location: str, year: int) -> str:
    return f"{location} {year} 年还没有焊接单价，请先到焊接单价页导入。"


def format_missing_breakdown(location: str, vehicle_model: str) -> str:
    return f"{location} {vehicle_model} 还没有焊接工艺拆解，请先到焊接工艺拆解页拆一次。"


def format_no_overlap(location: str, vehicle_model: str, year: int) -> str:
    return f"{location} {vehicle_model} 在 {year} 年没有有效期内的焊接拆解。"


def format_no_nodes(location: str, vehicle_model: str) -> str:
    return f"{location} {vehicle_model} 没有可算的零件。"
