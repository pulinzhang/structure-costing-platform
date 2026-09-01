"""计算开场：批次、过程日志头、空结果壳。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.common.timezone import now
from app.services.costing.steel_price.calc.models import (
    SteelPriceCalcRequest,
    SteelPriceCalcResult,
)
from app.services.costing.steel_price.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.steel_price.calc.process_log import ProcessLogBuilder


@dataclass(slots=True)
class CalcPrepContext:
    request: SteelPriceCalcRequest
    result: SteelPriceCalcResult
    log_builder: ProcessLogBuilder
    started_at: datetime
    calc_batch_id: str
    persist_log_started_at: datetime | None
    error_message: str | None = None


def prepare_calc_run(
    request: SteelPriceCalcRequest,
    progress: ProgressNotifier,
    *,
    calc_batch_id: str | None,
    started_at: datetime | None,
) -> CalcPrepContext:
    started = started_at or now()
    batch_id = calc_batch_id or f"calc-{uuid.uuid4().hex[:16]}"
    log_builder = ProcessLogBuilder()

    location = request.location.strip() if request.location else None
    stamping_supplier = request.stamping_supplier.strip() if request.stamping_supplier else None
    vehicle_model = request.vehicle_model.strip() if request.vehicle_model else None

    result = SteelPriceCalcResult(
        calc_batch_id=batch_id,
        year=request.year,
        month=request.month,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        started_at=started.isoformat(timespec="seconds"),
    )

    progress.report(1, "计算任务已启动")
    log_builder.section("计算开始")
    log_builder.line(f"批次号: {batch_id}")
    log_builder.line(f"核价期: {request.year}-{request.month:02d}")
    log_builder.line(f"生产基地: {location or '-'}")
    log_builder.line(f"冲压工厂: {stamping_supplier or '全部'}")
    log_builder.line(f"配套车型: {vehicle_model or '全部'}")
    log_builder.line(f"开始时间: {result.started_at}")

    return CalcPrepContext(
        request=request,
        result=result,
        log_builder=log_builder,
        started_at=started,
        calc_batch_id=batch_id,
        persist_log_started_at=started_at,
    )
