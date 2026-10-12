"""焊接费计算失败说明：给配置人员看的人话。"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.bom.welding_fee.calc.orchestrator.messages import (
    format_persist_summary,
    level_label,
)


@dataclass(slots=True, frozen=True)
class FailedNodeNote:
    level: int
    part_number: str
    part_name: str | None
    weld_info_raw: str | None
    calc_message: str | None
    excel_row: int | None = None
    excel_filename: str | None = None
    sheet_name: str | None = None


def human_failed_reason(calc_message: str | None) -> str:
    text = (calc_message or "").strip()
    if text.startswith("无焊接工艺明细"):
        return "材料清单有焊信，但拆解没拆出工艺行，本条焊接费按 0 元写入。"
    if text.startswith("全部缺单价"):
        return "拆出的工艺在本年本基地焊接单价里找不到，本条无法计价。"
    if text.startswith("无可用标准工艺映射"):
        return "拆出的行都没对上标准工艺，本条无法计价。"
    if text.startswith("部分缺单价"):
        return text
    return text or "本条计算失败，请到焊接费列表打开明细核对。"


def _excel_location(note: FailedNodeNote) -> str:
    filename = (
        note.excel_filename or ""
    ).strip() or "（未记录文件名，请到材料清单列表按基地/项目/版本下载原件）"
    sheet = (note.sheet_name or "").strip()
    row = note.excel_row
    parts = [f"Excel「{filename}」"]
    if sheet:
        parts.append(f"工作表「{sheet}」")
    if row is not None and int(row) > 0:
        parts.append(f"第 {int(row)} 行")
    else:
        parts.append(f"请按零件号 {note.part_number} 查找对应行")
    return "，".join(parts)


def weld_info_hint(weld_info_raw: str | None) -> str | None:
    weld = (weld_info_raw or "").strip()
    if not weld:
        return "该行焊接信息是空的。若本件要计焊接费，请补上「工序名：数量」。"
    compact = weld.replace(" ", "")
    if "：：" in compact or ":：" in compact or "：:" in compact or "::" in compact:
        return "该行焊信有连续冒号（例如「凸焊:：2」），请改成「凸焊：2」。"
    if any(token in weld for token in ("电泳", "黑漆", "涂装")):
        return "该行更像电泳/涂装面积，不是焊接工序。若本件要计焊接费，请改成焊接工序写法；否则可把该行焊信清空后重导。"
    if "焊缝" in weld:
        return (
            "「焊缝：N条 NNmm」应按 CO2焊缝拆解（括号可有可无）。"
            "不必改材料清单，请重新做焊接工艺拆解后再算焊接费。"
        )
    return "请把该行焊接信息改成「工序名：数量」（例如「凸焊：2」）。"


def excel_reimport_advice(note: FailedNodeNote) -> str:
    hint = weld_info_hint(note.weld_info_raw)
    weld = (note.weld_info_raw or "").strip()
    if "焊缝" in weld and not any(token in weld for token in ("电泳", "黑漆", "涂装")):
        return hint or "请重新做焊接工艺拆解后再算焊接费。"
    location = _excel_location(note)
    action = (
        f"请打开 {location}，改焊接信息列后保存，"
        "到「焊接工程 → 材料清单 → 上传材料清单」重新导入该版本，"
        "再重新做焊接工艺拆解，最后再算焊接费。"
    )
    if hint:
        return f"{hint} {action}"
    return action


def format_failed_node_block(note: FailedNodeNote) -> str:
    name = (note.part_name or "").strip() or "（无名称）"
    weld = (note.weld_info_raw or "").strip() or "（没写焊接信息）"
    lines = [
        f"{level_label(note.level)}  {note.part_number}  {name}",
        f"来源：{_excel_location(note)}",
        f"原因：{human_failed_reason(note.calc_message)}",
        f"焊接信息：{weld}",
    ]
    no_lines = (note.calc_message or "").startswith("无焊接工艺明细")
    empty_weld = not (note.weld_info_raw or "").strip()
    if no_lines or empty_weld:
        lines.append(f"建议：{excel_reimport_advice(note)}")
    return "\n".join(lines)


def format_failed_staff_section(notes: list[FailedNodeNote]) -> list[str]:
    if not notes:
        return []
    lines = [
        f"需配置人员处理 {len(notes)} 条（已写入列表，金额为 0）。"
        "请按下面的 Excel 文件名和第几行改材料清单，重新导入后再拆解、再计算：",
        "",
    ]
    for index, note in enumerate(notes):
        if index:
            lines.append("")
        lines.append(format_failed_node_block(note))
    return lines


def calc_finish_toast(
    *,
    biz_status: str,
    created_count: int,
    updated_count: int,
    failed_count: int,
    missing_price_count: int,
    skipped_approved_count: int = 0,
) -> str:
    label = {"success": "成功", "partial": "部分成功", "failed": "失败"}.get(biz_status, biz_status)
    summary = format_persist_summary(
        created_count,
        updated_count,
        failed_count,
        missing_price_count,
        skipped_approved_count,
        point_at_reasons=False,
    )
    text = f"计算{label}：{summary}"
    if failed_count:
        return (
            f"{text}没算上的写了 Excel 文件名和第几行，"
            "请改材料清单后重新导入，再拆一次，再计算。"
        )
    return text
