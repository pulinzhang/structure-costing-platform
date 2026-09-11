"""计算报告状态文案、筛选摘要、时间展示。"""

from datetime import datetime
from typing import Literal

TreeRootFilter = Literal["all", "yes", "no"]

STATUS_LABEL: dict[str, str] = {
    "ok": "成功",
    "partial": "部分成功",
    "failed": "失败",
    "skipped": "跳过",
    "processing": "计算中",
    "success": "成功",
}

STATUS_COLOR: dict[str, str] = {
    "ok": "71717A",
    "partial": "B45309",
    "failed": "B91C1C",
    "skipped": "57534E",
    "processing": "1D4ED8",
    "success": "71717A",
}


def status_label(status: str | None) -> str:
    if not status:
        return ""
    return STATUS_LABEL.get(status, status)


def format_when(value: datetime | None) -> str:
    if value is None:
        return "—"
    return f"{value:%Y-%m-%d %H:%M:%S}"


def report_filter_text(
    *,
    keyword: str | None,
    status: str | None,
    level: int | None,
    tree_root: TreeRootFilter,
    shown: int,
    total: int,
) -> str:
    parts: list[str] = [f"显示 {shown} / {total} 张卡"]
    if status:
        parts.append(status_label(status))
    if level is not None:
        parts.append(f"L{level}")
    if tree_root == "yes":
        parts.append("仅树根")
    elif tree_root == "no":
        parts.append("非树根")
    if keyword and keyword.strip():
        parts.append(f"关键词 {keyword.strip()}")
    return " · ".join(parts)
