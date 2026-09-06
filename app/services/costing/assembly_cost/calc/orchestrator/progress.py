"""编排进度通知：主流程只报阶段，逐件进度由引擎调用 tick。"""

from __future__ import annotations

from collections.abc import Callable

ProgressCallback = Callable[[int, str], None]


class ProgressNotifier:
    def __init__(self, callback: ProgressCallback | None = None) -> None:
        self._callback = callback

    def report(self, progress: int, message: str) -> None:
        if self._callback:
            self._callback(progress, message)

    def tick_parts(self, index: int, total: int) -> None:
        if total <= 0:
            return
        if index != total and index % 5 != 0:
            return
        pct = 25 + int(70 * index / total)
        self.report(pct, f"已处理 {index}/{total}")
