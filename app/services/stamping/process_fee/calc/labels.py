"""工序展示与共模/摆剪判定（纯函数，无 IO）。"""

from __future__ import annotations

from app.models.stamping import StampingPart, StampingProcess


def is_merged_process_method(text: str | None) -> bool:
    """文本含「合并」「双槽」「共用」：与上一零件共模同冲。"""
    if not text:
        return False
    value = str(text).strip()
    return "合并" in value or "双槽" in value or "共用" in value


def is_swing_shear_process(process: StampingProcess) -> bool:
    """摆剪工序不使用冲压，加工费为 0。"""
    code = (process.process_code or "").strip()
    seq = (process.process_seq or "").strip()
    return "摆剪" in code or "摆剪" in seq


def is_tailor_weld_describe_process(process: StampingProcess) -> bool:
    """拼焊描述工序（如「两块方料&拼焊」），不使用冲压，加工费为 0。"""
    code = (process.process_code or "").strip()
    seq = (process.process_seq or "").strip()
    return "拼焊" in code or "拼焊" in seq


def self_tonnage(process: StampingProcess) -> int | None:
    """
    工序自有吨位。0 与空均视为未填。

    Excel 共模右件吨位格常为空；解析曾把空写成 0，不能当 0T 压机。
    """
    if process.tonnage is None:
        return None
    value = int(process.tonnage)
    return value if value > 0 else None


def can_inherit_previous_tonnage(
    part: StampingPart,
    process: StampingProcess,
) -> bool:
    """
    共模件判定：零件工艺方法，或当前/同件任一道工序代码含「合并」「双槽」「共用」。
    Excel 常把「左右合并」「双槽」「共用」写在工序代码而非零件工艺方法字段。
    """
    if is_merged_process_method(part.process_method):
        return True
    if is_merged_process_method(process.process_code):
        return True
    for sibling in part.processes or []:
        if is_merged_process_method(sibling.process_code):
            return True
    return False


def format_merge_signal_label(
    part: StampingPart,
    process: StampingProcess,
) -> str:
    """错误/日志用：展示触发共模继承的文本来源。"""
    method = (part.process_method or "").strip()
    if is_merged_process_method(method):
        return method
    code = (process.process_code or "").strip()
    if is_merged_process_method(code):
        return code
    for sibling in part.processes or []:
        sibling_code = (sibling.process_code or "").strip()
        if is_merged_process_method(sibling_code):
            seq = (sibling.process_seq or "").strip() or "?"
            return f"{seq}/{sibling_code}"
    if method:
        return method
    if code:
        return code
    return "(空)"


def format_process_label(process: StampingProcess | None) -> str:
    """错误提示用：工序号 + 工序代码/名称。"""
    if process is None:
        return "?"
    seq = (process.process_seq or "").strip() or "?"
    code = (process.process_code or "").strip()
    if code:
        return f"{seq}/{code}"
    return seq


def summarize_processes(processes: list[StampingProcess]) -> str:
    """上一件工序清单，便于测试对照。"""
    if not processes:
        return "无工序"
    items: list[str] = []
    for process in sorted(
        processes, key=lambda p: (p.process_order or 0, p.id or 0)
    ):
        label = format_process_label(process)
        own = self_tonnage(process)
        tonnage_text = "无吨位" if own is None else f"{own}T"
        items.append(f"{label}={tonnage_text}")
    return "；".join(items)


def match_previous_process(
    process: StampingProcess,
    previous_processes: list[StampingProcess],
) -> StampingProcess | None:
    """按工序序号优先、其次工序顺序，匹配上一零件的对应工序。"""
    seq = (process.process_seq or "").strip()
    if seq:
        for prev in previous_processes:
            if (prev.process_seq or "").strip() == seq:
                return prev
    order = process.process_order
    if order is not None:
        for prev in previous_processes:
            if prev.process_order == order:
                return prev
    return None
