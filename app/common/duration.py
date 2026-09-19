"""起止时间 → 耗时秒。

唯一公式源。VO 经 ``app.schemas.vo.timing.DurationSecondsMixin`` 暴露
``duration_seconds``；Worker result / 过程日志「耗时」行等非 VO 载荷也调本函数。

禁止在各切片再写 ``(finished - started).total_seconds()`` 当作对外契约
（API 字段、历史列表、worker JSON）。僵死锁年龄等非「运行耗时」语义除外。
"""

from __future__ import annotations

from datetime import datetime


def duration_seconds(started_at: datetime | None, finished_at: datetime | None) -> int | None:
    """两端齐全时返回非负整秒；否则 None（进行中或数据不齐）。"""
    if started_at is None or finished_at is None:
        return None
    return max(0, int(round((finished_at - started_at).total_seconds())))
