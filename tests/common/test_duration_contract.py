"""运行历史耗时：秒数公式。"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.common.duration import duration_seconds


def test_duration_seconds_both_ends() -> None:
    start = datetime(2026, 1, 1, 12, 0, 0)
    end = start + timedelta(seconds=45)
    assert duration_seconds(start, end) == 45


def test_duration_seconds_missing_end_is_none() -> None:
    start = datetime(2026, 1, 1, 12, 0, 0)
    assert duration_seconds(start, None) is None
    assert duration_seconds(None, start) is None
    assert duration_seconds(None, None) is None


def test_duration_seconds_never_negative() -> None:
    start = datetime(2026, 1, 1, 12, 0, 10)
    end = datetime(2026, 1, 1, 12, 0, 0)
    assert duration_seconds(start, end) == 0
