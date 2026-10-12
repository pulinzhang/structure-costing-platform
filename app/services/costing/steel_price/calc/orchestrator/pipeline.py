"""钢价管道：串联材料加载 / 基价 / 加减价 / 落库。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.operator_copy import OPERATOR_CALC_INTERRUPTED
from app.exceptions.base import BusinessException
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.calc.coverage import raise_if_thickness_gaps
from app.services.costing.steel_price.calc.orchestrator.deps import SteelPriceCalcDeps
from app.services.costing.steel_price.calc.orchestrator.messages import (
    format_base_hits,
    format_materials,
    format_policies,
    format_saved,
    format_thickness,
    format_width_skipped,
)
from app.services.costing.steel_price.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.steel_price.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.steel_price.calc.status import (
    STATUS_FAILED,
    collect_row_warnings,
    resolve_batch_status,
    summarize_thickness_outcomes,
)
from app.services.costing.steel_price.service import FORMULA_VERSION

logger = logging.getLogger("service.steel_price.calc")


class SteelPricePipeline:
    def __init__(self, deps: SteelPriceCalcDeps) -> None:
        self._deps = deps

    def run(
        self,
        db: Session,
        ctx: CalcPrepContext,
        current_user: UserVO,
        progress: ProgressNotifier,
    ) -> CalcPrepContext:
        result = ctx.result
        log_builder = ctx.log_builder
        request = ctx.request
        calc_batch_id = ctx.calc_batch_id
        location = request.location.strip()

        try:
            if not location:
                raise BusinessException("请先选择生产基地。")

            progress.report(10, "正在读取材料规格…")
            materials = self._deps.material_loader.load(db, request)
            result.material_count = len(materials)
            log_builder.line(format_materials(result.material_count))
            progress.report(20, f"材料规格 {result.material_count} 种")

            progress.report(25, "正在对照基价…")
            rows, no_base_count, no_base_details = self._deps.base_price_enricher.enrich(
                db, request, materials
            )
            result.enriched_count = len(rows)
            result.no_base_count = no_base_count
            log_builder.line(format_base_hits(result.enriched_count, result.no_base_count))
            log_builder.append_limited_details("没有基价的牌号", no_base_details, is_error=True)
            progress.report(
                40,
                f"对上基价 {result.enriched_count} 行，缺基价 {result.no_base_count} 个牌号",
            )

            policies = self._deps.adjustment_applier.load_policies(db, request)

            progress.report(45, "正在对照厚度加减价…")
            log_builder.line(format_policies(len(policies)))
            rows = self._deps.adjustment_applier.apply_thickness(db, rows, policies)
            thickness = summarize_thickness_outcomes(rows)
            for line in format_thickness(
                thickness["hit"],
                thickness["skip"],
                thickness["miss"],
                thickness["skip_mills"],
            ):
                log_builder.line(line)
            log_builder.append_limited_details(
                "没对上厚度加减价",
                collect_row_warnings(rows, keyword="厚度"),
                is_error=True,
            )
            raise_if_thickness_gaps(rows)
            progress.report(
                55,
                f"厚度加减价对上 {thickness['hit']} 行，没对上 {thickness['miss']} 行",
            )

            progress.report(60, "宽度加减价这次不算…")
            log_builder.line(format_width_skipped())
            rows = self._deps.adjustment_applier.apply_width(rows, policies)
            progress.report(70, "宽度加减价已跳过")

            progress.report(75, "正在写入钢材联动价…")
            persist_stats = self._deps.steel_price_service.save_calc_batch(
                db,
                calc_batch_id=calc_batch_id,
                rows=[
                    row.to_persist_payload(
                        calc_batch_id=calc_batch_id,
                        formula_version=FORMULA_VERSION,
                    )
                    for row in rows
                    if row.can_persist()
                ],
                current_user=current_user,
            )
            result.created_count = persist_stats["created_count"]
            result.updated_count = persist_stats["updated_count"]
            result.skipped_approved_count = persist_stats["skipped_approved_count"]
            result.failed_count = persist_stats["failed_count"]
            log_builder.line(
                format_saved(
                    result.created_count,
                    result.updated_count,
                    result.skipped_approved_count,
                    result.failed_count,
                )
            )

            result.status = resolve_batch_status(result, rows)
            progress.report(92, "正在写入计算过程…")
        except (BusinessException, ValueError) as error:
            result.status = STATUS_FAILED
            log_builder.error(str(error))
            ctx.error_message = str(error)
        except Exception as error:
            result.status = STATUS_FAILED
            log_builder.error(OPERATOR_CALC_INTERRUPTED)
            logger.exception("钢价计算失败: batch=%s error=%s", calc_batch_id, error)
            ctx.error_message = OPERATOR_CALC_INTERRUPTED

        return ctx
