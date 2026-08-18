"""焊接工艺拆解生成 — 过程文本构建。"""

from __future__ import annotations


class ProcessLogBuilder:
    """累积拆解过程文本。"""

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
