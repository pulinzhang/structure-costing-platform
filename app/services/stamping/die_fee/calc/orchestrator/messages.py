"""冲压模具费计算过程文案（给人看，不写字段名）。"""

from __future__ import annotations

from app.services.stamping.die_fee.calc.constants import ALL_SUPPLIERS_LOCK

_SKIP_REASON = "没有模具尺寸或重量，算不出钱；家模带出来的小件也不记模具费"


def format_prep_opening(
    year: int,
    location: str,
    vehicle_model: str,
    version: str | None,
) -> str:
    line = f"开始计算：{year}年，{location}，{vehicle_model}，{ALL_SUPPLIERS_LOCK}"
    if version:
        line += f"，版本 {version}"
    return line


def format_layout_scope(persist_count: int, scan_count: int) -> str:
    if persist_count == scan_count:
        return f"有效期内的模具布点 {persist_count} 件，这次都要算。"
    return (
        f"这次要算 {persist_count} 件。" f"左右件共用一套模具，对照时看了整份布点 {scan_count} 件。"
    )


def format_persist_summary(success_count: int, skipped_count: int) -> str:
    if skipped_count <= 0:
        return f"写入模具费 {success_count} 件，没有跳过。"
    if success_count <= 0:
        return f"没有写入模具费。{skipped_count} 件都跳过了：{_SKIP_REASON}。"
    return f"写入模具费 {success_count} 件。另外 {skipped_count} 件没写入：{_SKIP_REASON}。"


def format_all_skipped_hint() -> str:
    return (
        "一件都没写入：这些零件的工序上没有模具重量，旁边的零件也借不到外形。"
        "请确认上传的是带模具尺寸和重量的布点清单，不是工艺确认表。"
    )


def format_calc_finished_log(
    year: int,
    location: str,
    vehicle_model: str,
    success_count: int,
    skipped_count: int,
) -> str:
    return (
        f"冲压模具费计算完成：{year}年，{location}，{vehicle_model}，"
        f"写入 {success_count} 件，跳过 {skipped_count} 件"
    )
