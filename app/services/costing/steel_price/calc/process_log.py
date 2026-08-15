"""计算过程文本构建（detail_text）。"""

from __future__ import annotations

DETAIL_ITEM_LIMIT = 200


class ProcessLogBuilder:
    """累积计算过程文本（含错误）。"""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def line(self, message: str) -> None:
        self._lines.append(message)

    def section(self, title: str) -> None:
        self._lines.append("")
        self._lines.append(f"=== {title} ===")

    def error(self, message: str) -> None:
        self._lines.append(f"[错误] {message}")

    def warn(self, message: str) -> None:
        self._lines.append(f"[警告] {message}")

    def build(self) -> str:
        return "\n".join(self._lines).strip() + ("\n" if self._lines else "")

    def append_limited_details(
        self,
        title: str,
        items: list[str],
        *,
        is_error: bool,
        limit: int = DETAIL_ITEM_LIMIT,
    ) -> None:
        if not items:
            return
        self.line(f"{title}（共 {len(items)} 条，最多展示 {limit}）:")
        shown = items[:limit]
        for item in shown:
            if is_error:
                self.error(item)
            else:
                self.line(f"  - {item}")
        omitted = len(items) - len(shown)
        if omitted > 0:
            self.warn(f"另有 {omitted} 条未展开")
