"""编排进度通知。"""

from __future__ import annotations

from collections.abc import Callable

ProgressCallback = Callable[[int, str], None]


class ProgressNotifier:
    def __init__(self, callback: ProgressCallback | None = None) -> None:
        self._callback = callback

    def report(self, progress: int, message: str) -> None:
        if self._callback:
            self._callback(progress, message)
