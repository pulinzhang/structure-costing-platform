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
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.steel_price.calc.calc_log_service import CalcLogService
from app.services.steel_price.calc.models import (
    SteelPriceCalcRequest,
    SteelPriceCalcResult,
)
from app.services.steel_price.calc.process_log import ProcessLogBuilder
from app.services.steel_price.calc.status import (
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


class SteelPriceCalcOrchestrator:
    """钢材价格计算编排器。"""

    def __init__(self) -> None:
        self.material_loader = MaterialThicknessLoader()
        self.base_price_enricher = BasePriceEnricher()
        self.adjustment_applier = AdjustmentApplier()
        self.steel_price_service = SteelPriceService()
        self.calc_log_service = CalcLogService()

    def calculate(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
    ) -> SteelPriceCalcResult:
        """
        执行完整计算编排。

        无论成功或失败，都会尽量写入一条计算日志（detail_text）。
        """
        started_at = datetime.now()
        calc_batch_id = f"calc-{uuid.uuid4().hex[:16]}"
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
            log_builder.section("Step1 材料厚度列表")
            materials = self.material_loader.load(db, normalized)
            result.material_count = len(materials)
            log_builder.line(f"去重材料+厚度规格: {result.material_count} 条")
            if result.material_count == 0:
                log_builder.warn("未取到任何材料厚度规格，后续无法产出结果行")

            # Step 2
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

            # Step 3/4 — 加减价政策只查一次，厚度/宽度分步匹配
            policies = self.adjustment_applier.load_policies(db, normalized)

            # Step 3 — 厚度加减价（独立）
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

            # Step 4 — 宽度加减价（独立）
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

            # Step 5
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

        except Exception as error:
            result.status = "failed"
            log_builder.section("计算异常")
            log_builder.error(str(error))
            log_builder.line(traceback.format_exc())
            logger.exception("钢价计算失败: batch=%s error=%s", calc_batch_id, error)
            finished_at = datetime.now()
            result.finished_at = finished_at.isoformat(timespec="seconds")
            result.detail_text = log_builder.build()
            result.log_id = self.calc_log_service.persist(
                db,
                result=result,
                started_at=started_at,
                finished_at=finished_at,
            )
            raise

        finished_at = datetime.now()
        result.finished_at = finished_at.isoformat(timespec="seconds")
        log_builder.line(f"结束时间: {result.finished_at}")
        log_builder.line(f"耗时: {(finished_at - started_at).total_seconds():.2f}s")
        result.detail_text = log_builder.build()
        result.log_id = self.calc_log_service.persist(
            db,
            result=result,
            started_at=started_at,
            finished_at=finished_at,
        )
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
