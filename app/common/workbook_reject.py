"""整本拒绝时给操作员的提示：逐条写明行、列和改法。"""

from __future__ import annotations

_SHOWN_LIMIT = 20

EMPTY_FILE = "文件是空的。请重新选择已经填好的 .xlsx。"
UNREADABLE_EXCEL = "无法读取 Excel。请用 Excel 打开后另存为 .xlsx，再重新上传。"
NO_WORKSHEET = "工作簿里没有工作表。请确认第一张表有数据后再上传。"
NO_DATA_ROWS = "没有可导入的数据行。请从第 2 行起填写，不要只留表头。"


def describe_cell(value: object) -> str:
    """把单元格原值收成操作员能看的短文本。"""
    if value is None:
        return "空"
    text = str(value).strip()
    if not text:
        return "空"
    if len(text) > 40:
        return text[:40] + "…"
    return text


def invalid_amount(row_number: int, column: str, raw: object, example: str) -> str:
    """金额列：空或不是数字时，指出这一格并给出填法。"""
    shown = describe_cell(raw)
    if shown == "空":
        return f"第 {row_number} 行「{column}」是空的。" f"请填大于等于 0 的数字，例如 {example}。"
    return (
        f"第 {row_number} 行「{column}」填了「{shown}」，不是有效金额。"
        f"请改成大于等于 0 的数字，例如 {example}。"
    )


def format_workbook_reject(errors: list[str], *, catalog: bool = False) -> str:
    """整本未写入。首行说明后果，后面每条错误单独一行。"""
    if catalog:
        lead = (
            "导入中止。名称和单位必须与标准工艺目录完全一致。"
            "整本未导入，没有任何一行写入。请按下面改完后再上传："
        )
    else:
        lead = "整本未导入，没有任何一行写入。请按下面改完后再上传："
    shown = [line.strip() for line in errors if line and line.strip()]
    if not shown:
        return lead
    body = shown[:_SHOWN_LIMIT]
    lines = [lead, *[f"· {line}" for line in body]]
    rest = len(shown) - len(body)
    if rest:
        lines.append(f"还有 {rest} 条没有列在这里。请先改完上面这些，再重新上传。")
    return "\n".join(lines)
