"""
钢价计算编排器（只负责串联步骤，不含具体匹配/落库细节）

计算链：
  1. MaterialThicknessLoader  — 材料厚度
  2. BasePriceEnricher        — 基价补齐
  3. AdjustmentApplier.apply_thickness — 厚度加减价（共用一次加载的政策）
  4. AdjustmentApplier.apply_width     — 宽度加减价（共用一次加载的政策）
  5. SteelPriceService        — 结果落库
  6. CalcLogService           — 过程日志（detail_text）
"""

from __future__ import annotations

import logging
import traceback
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.services.steel_price.calc.calc_log_service import CalcLogService
from app.services.steel_price.calc.models import (
    SteelPriceCalcRequest,
    SteelPriceCalcResult,
)
from app.schemas.vo.user_vo import UserVO
from app.services.steel_price.calc.process_log import ProcessLogBuilder
from app.services.steel_price.calc.status import (
    STATUS_FAILED,
    collect_row_warnings,
    resolve_batch_status,
    summarize_match_status,
    summarize_policy_hits,
)
from app.services.steel_price.calc.steps import (
    AdjustmentApplier,
    BasePriceEnricher,
    MaterialThicknessLoader,
)
from app.services.steel_price.steel_price_service import FORMULA_VERSION, SteelPriceService


logger = logging.getLogger("service.steel_price.calc")

ProgressCallback = Callable[[int, str], None]


class SteelPriceCalcOrchestrator:
    """钢材价格计算编排器。"""

    def __init__(self) -> None:
        self.material_loader = MaterialThicknessLoader()
        self.base_price_enricher = BasePriceEnricher()
        self.adjustment_applier = AdjustmentApplier()
        self.steel_price_service = SteelPriceService()
        self.calc_log_service = CalcLogService()

    def begin_processing(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        *,
        operator_id: int | None = None,
        operator_name: str | None = None,
    ):
        """提交前写入 processing 期别锁。"""
        location = (request.location or "").strip()
        if not location:
            raise ValueError("计算钢价必须指定生产基地 location")
        return self.calc_log_service.begin_processing(
            db,
            year=request.year,
            month=request.month,
            location=location,
            stamping_supplier=(
                request.stamping_supplier.strip() if request.stamping_supplier else None
            ),
            vehicle_model=(
                request.vehicle_model.strip() if request.vehicle_model else None
            ),
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def is_period_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> bool:
        return self.calc_log_service.is_period_processing(
            db, year=year, month=month, location=location.strip()
        )

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        self.calc_log_service.mark_failed(
            db, log_id=log_id, message=message, detail_text=detail_text
        )

    def calculate(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        progress_callback: Optional[ProgressCallback] = None,
        *,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
        started_at: datetime | None = None,
        current_user: UserVO,
    ) -> SteelPriceCalcResult:
        """
        执行完整计算编排。

        若传入 log_id（提交时已写入的 processing 行），结束后更新该行；
        否则回退为新建终态日志。
        业务失败返回 status=failed 的结果，不再向外抛出（校验错误 ValueError 除外）。
        """
        def _report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        def _persist_log(result_obj: SteelPriceCalcResult, finished: datetime) -> int | None:
            if log_id is not None:
                return self.calc_log_service.finalize(
                    db,
                    log_id=log_id,
                    result=result_obj,
                    finished_at=finished,
                )
            return self.calc_log_service.persist(
                db,
                result=result_obj,
                started_at=started_at or finished,
                finished_at=finished,
            )

        started_at = started_at or now()
        calc_batch_id = calc_batch_id or f"calc-{uuid.uuid4().hex[:16]}"
        log_builder = ProcessLogBuilder()

        location = request.location.strip() if request.location else None
        stamping_supplier = (
            request.stamping_supplier.strip() if request.stamping_supplier else None
        )
        vehicle_model = request.vehicle_model.strip() if request.vehicle_model else None

        result = SteelPriceCalcResult(
            calc_batch_id=calc_batch_id,
            year=request.year,
            month=request.month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            started_at=started_at.isoformat(timespec="seconds"),
        )

        _report(1, "计算任务已启动")
        log_builder.section("计算开始")
        log_builder.line(f"批次号: {calc_batch_id}")
        log_builder.line(f"核价期: {request.year}-{request.month:02d}")
        log_builder.line(f"生产基地: {location or '-'}")
        log_builder.line(f"冲压工厂: {stamping_supplier or '全部'}")
        log_builder.line(f"配套车型: {vehicle_model or '全部'}")
        log_builder.line(f"开始时间: {result.started_at}")

        try:
            if not location:
                raise ValueError("计算钢价必须指定生产基地 location")

            normalized = SteelPriceCalcRequest(
                year=request.year,
                month=request.month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
            )

            # Step 1
            _report(10, "Step1：加载材料厚度规格...")
            log_builder.section("Step1 材料厚度列表")
            materials = self.material_loader.load(db, normalized)
            result.material_count = len(materials)
            log_builder.line(f"去重材料+厚度规格: {result.material_count} 条")
            if result.material_count == 0:
                log_builder.warn("未取到任何材料厚度规格，后续无法产出结果行")
            _report(20, f"Step1 完成：材料规格 {result.material_count} 条")

            # Step 2
            _report(25, "Step2：基价表补齐...")
            log_builder.section("Step2 基价表补齐")
            rows, no_base_count, no_base_details = self.base_price_enricher.enrich(
                db, normalized, materials
            )
            result.enriched_count = len(rows)
            result.no_base_count = no_base_count
            log_builder.line(f"命中基价并展开: {result.enriched_count} 行")
            log_builder.line(f"无基价/基价不完整: {result.no_base_count} 条")
            log_builder.append_limited_details(
                "无基价明细", no_base_details, is_error=True
            )
            _report(
                40,
                f"Step2 完成：命中 {result.enriched_count} 行，无基价 {result.no_base_count}",
            )

            # Step 3/4 — 加减价政策只查一次，厚度/宽度分步匹配
            policies = self.adjustment_applier.load_policies(db, normalized)

            # Step 3 — 厚度加减价（独立）
            _report(45, "Step3：厚度加减价匹配...")
            log_builder.section("Step3 厚度加减价匹配")
            log_builder.line(f"加减价政策加载: {len(policies)} 条（厚度/宽度共用，仅此一次）")
            rows = self.adjustment_applier.apply_thickness(rows, policies)
            thickness_hit, thickness_miss = summarize_policy_hits(rows, prefix="thickness")
            log_builder.line(f"厚度政策命中: {thickness_hit}")
            log_builder.line(f"厚度政策未命中: {thickness_miss}")
            log_builder.append_limited_details(
                "厚度未命中/警告",
                collect_row_warnings(rows, keyword="厚度"),
                is_error=True,
            )
            _report(55, f"Step3 完成：厚度命中 {thickness_hit}，未命中 {thickness_miss}")

            # Step 4 — 宽度加减价（独立）
            _report(60, "Step4：宽度加减价匹配...")
            log_builder.section("Step4 宽度加减价匹配")
            rows = self.adjustment_applier.apply_width(rows, policies)
            width_hit, width_miss = summarize_policy_hits(rows, prefix="width")
            log_builder.line(f"宽度政策命中: {width_hit}")
            log_builder.line(f"宽度政策未命中: {width_miss}")
            log_builder.append_limited_details(
                "宽度未命中/警告",
                collect_row_warnings(rows, keyword="宽度"),
                is_error=True,
            )
            for key, count in summarize_match_status(rows).items():
                log_builder.line(f"match_status={key}: {count}")
            _report(70, f"Step4 完成：宽度命中 {width_hit}，未命中 {width_miss}")

            # Step 5
            _report(75, "Step5：结果落库...")
            log_builder.section("Step5 结果落库")
            persist_stats = self.steel_price_service.save_calc_batch(
                db,
                calc_batch_id=calc_batch_id,
                rows=[
                    row.to_persist_payload(
                        calc_batch_id=calc_batch_id,
                        formula_version=FORMULA_VERSION,
                    )
                    for row in rows
                ],
                current_user=current_user,
            )
            result.created_count = persist_stats["created_count"]
            result.updated_count = persist_stats["updated_count"]
            result.skipped_approved_count = persist_stats["skipped_approved_count"]
            result.failed_count = persist_stats["failed_count"]
            log_builder.line(f"新增: {result.created_count}")
            log_builder.line(f"更新: {result.updated_count}")
            log_builder.line(f"跳过已审: {result.skipped_approved_count}")
            log_builder.line(f"落库失败: {result.failed_count}")

            result.status = resolve_batch_status(result, rows)
            log_builder.section("计算结束")
            log_builder.line(f"批次状态: {result.status}")
            _report(92, "写入计算过程日志...")

        except ValueError as error:
            result.status = STATUS_FAILED
            log_builder.section("计算校验失败")
            log_builder.error(str(error))
            finished_at = now()
            result.finished_at = finished_at.isoformat(timespec="seconds")
            result.detail_text = log_builder.build()
            result.log_id = _persist_log(result, finished_at)
            _report(100, f"计算失败: {error}")
            return result
        except Exception as error:
            result.status = STATUS_FAILED
            log_builder.section("计算异常")
            log_builder.error(str(error))
            log_builder.line(traceback.format_exc())
            logger.exception("钢价计算失败: batch=%s error=%s", calc_batch_id, error)
            finished_at = now()
            result.finished_at = finished_at.isoformat(timespec="seconds")
            result.detail_text = log_builder.build()
            result.log_id = _persist_log(result, finished_at)
            _report(100, f"计算失败: {error}")
            return result

        finished_at = now()
        result.finished_at = finished_at.isoformat(timespec="seconds")
        log_builder.line(f"结束时间: {result.finished_at}")
        log_builder.line(f"耗时: {(finished_at - started_at).total_seconds():.2f}s")
        result.detail_text = log_builder.build()
        result.log_id = _persist_log(result, finished_at)
        _report(100, f"计算完成：状态 {result.status}")
        return result

    def list_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        page: int = 1,
        size: int = 20,
    ):
        return self.calc_log_service.list_logs(
            db,
            year=year,
            month=month,
            location=location,
            page=page,
            size=size,
        )

    def get_log(self, db: Session, log_id: int):
        return self.calc_log_service.get_log(db, log_id)

    def delete_log(self, db: Session, log_id: int) -> bool:
        return self.calc_log_service.delete_log(db, log_id)
