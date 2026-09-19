"""运行历史 VO：起止时间 → `duration_seconds`。

契约（改历史列表前必读）：
1. Model / 落库：``started_at`` + ``finished_at``（未结束则 finished 为 null）。
2. VO：继承 ``DurationSecondsMixin``，由本模块统一算秒；禁止在各切片 VO 里复制公式。
3. JSON：``duration_seconds`` 为非负整秒或 null（未结束 / 缺一端）。
4. 前端：历史表列「开始 / 结束 / 耗时」，只走 ``static/js/duration.js``。

新增 CalcLog / GenerateLog / Engine Run 时：登记进
    ``calc_history_timing_vo_types()``，并跑 ``tests/common/test_duration_contract.py``。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, computed_field

from app.common.duration import duration_seconds as calc_duration_seconds

if TYPE_CHECKING:
    from collections.abc import Sequence


class DurationSecondsMixin(BaseModel):
    """子类须声明 ``started_at`` / ``finished_at``（及既有 datetime serializer）。"""

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def duration_seconds(self) -> int | None:
        return calc_duration_seconds(
            getattr(self, "started_at", None),
            getattr(self, "finished_at", None),
        )


def calc_history_timing_vo_types() -> Sequence[type[BaseModel]]:
    """须暴露 duration_seconds 的运行历史 VO（守卫测试登记册）。"""
    from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcLogVO
    from app.schemas.vo.bom_procurement_object_vo import BomProcurementObjectGenerateLogVO
    from app.schemas.vo.bom_welding_fee_vo import BomWeldingFeeCalcLogVO
    from app.schemas.vo.bom_welding_process_breakdown_vo import (
        BomWeldingProcessBreakdownGenerateLogVO,
    )
    from app.schemas.vo.costing_engine_vo import (
        CostingEngineRunListItemVO,
        CostingEngineRunStepVO,
        CostingEngineRunVO,
    )
    from app.schemas.vo.stamping_die_fee_vo import StampingDieFeeCalcLogVO
    from app.schemas.vo.stamping_part_cost_vo import StampingPartCostCalcLogVO
    from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeCalcLogVO
    from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO

    return (
        SteelPriceCalcLogVO,
        StampingPartCostCalcLogVO,
        AssemblyCostCalcLogVO,
        StampingProcessFeeCalcLogVO,
        StampingDieFeeCalcLogVO,
        BomWeldingFeeCalcLogVO,
        BomWeldingProcessBreakdownGenerateLogVO,
        BomProcurementObjectGenerateLogVO,
        CostingEngineRunVO,
        CostingEngineRunListItemVO,
        CostingEngineRunStepVO,
    )
