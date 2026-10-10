"""运行历史 VO：起止时间 → `duration_seconds`。

契约（改历史列表前必读）：
1. Model / 落库：``started_at`` + ``finished_at``（未结束则 finished 为 null）。
2. VO：继承 ``DurationSecondsMixin``，由本模块统一算秒；禁止在各切片 VO 里复制公式。
3. JSON：``duration_seconds`` 为非负整秒或 null（未结束 / 缺一端）。
4. 前端：历史表列「开始 / 结束 / 耗时」，只走 ``static/js/duration.js``。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, computed_field

from app.common.duration import duration_seconds as calc_duration_seconds


class DurationSecondsMixin(BaseModel):
    """子类须声明 ``started_at`` / ``finished_at``（及既有 datetime serializer）。"""

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def duration_seconds(self) -> int | None:
        return calc_duration_seconds(
            getattr(self, "started_at", None),
            getattr(self, "finished_at", None),
        )
