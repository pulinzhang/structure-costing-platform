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
from app.services.costing.steel_price.calc.orchestrator.messages import format_prep_opening
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

    location = request.location.strip()
    request = SteelPriceCalcRequest(
        year=request.year,
        month=request.month,
        location=location,
    )

    result = SteelPriceCalcResult(
        calc_batch_id=batch_id,
        year=request.year,
        month=request.month,
        location=location or None,
        started_at=started.isoformat(timespec="seconds"),
    )

    progress.report(1, "正在计算…")
    log_builder.line(format_prep_opening(request.year, request.month, location))

    return CalcPrepContext(
        request=request,
        result=result,
        log_builder=log_builder,
        started_at=started,
        calc_batch_id=batch_id,
        persist_log_started_at=started_at,
    )
