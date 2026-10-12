"""钢材联动价计算过程文案（给人看，不写字段名）。"""

from __future__ import annotations

from app.common.period import format_period


def format_prep_opening(year: int, month: int, location: str) -> str:
    place = location or "未选基地"
    return f"开始计算：{format_period(year, month)}，{place}。"


def format_materials(count: int) -> str:
    if count <= 0:
        return "没有取到材料规格，后面算不出价格。"
    return f"材料规格 {count} 种。"


def format_base_hits(enriched_count: int, missing_count: int) -> str:
    if missing_count <= 0:
        return f"对上基价并展开 {enriched_count} 行。基价都齐。"
    return f"对上基价并展开 {enriched_count} 行。还有 {missing_count} 个牌号没有基价或不完整。"


def format_policies(policy_count: int) -> str:
    return f"厚度加减价政策 {policy_count} 条。"


def format_thickness(hit: int, skip: int, miss: int, skip_mills: list[str]) -> list[str]:
    lines = [f"厚度加减价对上 {hit} 行。"]
    if skip:
        mills = "、".join(skip_mills) or "未注明钢厂"
        lines.append(f"有 {skip} 行这家钢厂本期没有厚度加减价，按基价算，不算错（钢厂：{mills}）。")
    if miss:
        lines.append(f"还有 {miss} 行没对上厚度加减价。")
    else:
        lines.append("该对的厚度加减价都对上了。")
    return lines


def format_width_skipped() -> str:
    return "宽度加减价这次不算。"


def format_saved(created: int, updated: int, skipped: int, failed: int) -> str:
    if created and updated:
        head = f"新写入 {created} 条，重算 {updated} 条"
    elif created:
        head = f"新写入钢材联动价 {created} 条"
    elif updated:
        head = f"重算钢材联动价 {updated} 条"
    else:
        head = "没有写入钢材联动价"
    notes: list[str] = []
    if skipped:
        notes.append(f"{skipped} 条已经审核过，这次没重算")
    if failed:
        notes.append(f"{failed} 条没写入")
    if notes:
        return f"{head}。{'。'.join(notes)}。"
    if created or updated:
        return f"{head}。"
    return f"{head}。"


def format_unclassified(location: str, grade: str) -> str:
    return f"{location} 的 {grade} 还没分成冷轧、镀锌或酸洗，对不上基价。"


def format_missing_grade(location: str, grade: str, category_name: str) -> str:
    return f"{location} 的 {grade}（{category_name}）在基价表里没有这个牌号。"


def format_base_location_mismatch(location: str, grade: str, base_location: str) -> str:
    return f"{location} 的 {grade} 对上的基价属于 {base_location}，基地不一致。"
