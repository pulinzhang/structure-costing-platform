"""编排进度通知：主流程只报阶段，逐件进度由引擎调用 tick。"""

from __future__ import annotations

from app.services.stamping.process_fee.calc.models import ProgressCallback


class ProgressNotifier:
    def __init__(self, callback: ProgressCallback | None = None) -> None:
        self._callback = callback

    def report(self, progress: int, message: str) -> None:
        if self._callback:
            self._callback(progress, message)

    def tick_parts(self, index: int, total: int) -> None:
        if total <= 0:
            return
        if index != total and index % 20 != 0:
            return
        pct = 10 + int(80 * index / total)
        self.report(pct, f"计算中 {index}/{total}...")
