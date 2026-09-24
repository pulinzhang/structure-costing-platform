"""钢价管道：串联材料加载 / 基价 / 加减价 / 落库。"""

from __future__ import annotations

import logging
import traceback

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.calc.coverage import raise_if_thickness_gaps
from app.services.costing.steel_price.calc.orchestrator.deps import SteelPriceCalcDeps
from app.services.costing.steel_price.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.steel_price.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.steel_price.calc.status import (
    STATUS_FAILED,
    collect_row_warnings,
    resolve_batch_status,
    summarize_match_status,
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
                raise BusinessException("计算钢价必须指定生产基地 location")

            progress.report(10, "Step1：加载材料厚度规格...")
            log_builder.section("Step1 材料厚度列表")
            materials = self._deps.material_loader.load(db, request)
            result.material_count = len(materials)
            log_builder.line(f"去重材料+厚度规格: {result.material_count} 条")
            if result.material_count == 0:
                log_builder.warn("未取到任何材料厚度规格，后续无法产出结果行")
            progress.report(20, f"Step1 完成：材料规格 {result.material_count} 条")

            progress.report(25, "Step2：基价表补齐...")
            log_builder.section("Step2 基价表补齐")
            rows, no_base_count, no_base_details = self._deps.base_price_enricher.enrich(
                db, request, materials
            )
            result.enriched_count = len(rows)
            result.no_base_count = no_base_count
            log_builder.line(f"命中基价并展开: {result.enriched_count} 行")
            log_builder.line(f"无基价/基价不完整: {result.no_base_count} 条")
            log_builder.append_limited_details("无基价明细", no_base_details, is_error=True)
            progress.report(
                40,
                f"Step2 完成：命中 {result.enriched_count} 行，无基价 {result.no_base_count}",
            )

            policies = self._deps.adjustment_applier.load_policies(db, request)

            progress.report(45, "Step3：厚度加减价匹配...")
            log_builder.section("Step3 厚度加减价匹配")
            log_builder.line(f"加减价政策加载: {len(policies)} 条（仅厚度大类）")
            rows = self._deps.adjustment_applier.apply_thickness(db, rows, policies)
            thickness = summarize_thickness_outcomes(rows)
            log_builder.line(f"厚度政策命中: {thickness['hit']}")
            if thickness["skip"] > 0:
                mills = "、".join(thickness["skip_mills"]) or "无"
                log_builder.line(
                    f"本期无该厂厚度块（按基价计，不报错）: {thickness['skip']}（钢厂：{mills}）"
                )
            log_builder.line(f"厚度政策未命中: {thickness['miss']}")
            log_builder.append_limited_details(
                "厚度未命中/警告",
                collect_row_warnings(rows, keyword="厚度"),
                is_error=True,
            )
            raise_if_thickness_gaps(rows)
            progress.report(
                55,
                f"Step3 完成：厚度命中 {thickness['hit']}，未命中 {thickness['miss']}",
            )

            progress.report(60, "Step4：宽度加减价（本期跳过）...")
            log_builder.section("Step4 宽度加减价")
            log_builder.line("宽度加减价本期不应用")
            rows = self._deps.adjustment_applier.apply_width(rows, policies)
            log_builder.line("宽度政策命中: 0")
            log_builder.line("宽度政策未命中: 0")
            for key, count in summarize_match_status(rows).items():
                log_builder.line(f"match_status={key}: {count}")
            progress.report(70, "Step4 完成：宽度加减价已跳过")

            progress.report(75, "正在保存计算结果...")
            log_builder.section("Step5 结果落库")
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
            log_builder.line(f"新增: {result.created_count}")
            log_builder.line(f"更新: {result.updated_count}")
            log_builder.line(f"跳过已审: {result.skipped_approved_count}")
            log_builder.line(f"落库失败: {result.failed_count}")

            result.status = resolve_batch_status(result, rows)
            log_builder.section("计算结束")
            log_builder.line(f"批次状态: {result.status}")
            progress.report(92, "写入计算过程日志...")
        except (BusinessException, ValueError) as error:
            result.status = STATUS_FAILED
            log_builder.section("计算校验失败")
            log_builder.error(str(error))
            ctx.error_message = str(error)
        except Exception as error:
            result.status = STATUS_FAILED
            log_builder.section("计算异常")
            log_builder.error(str(error))
            log_builder.line(traceback.format_exc())
            logger.exception("钢价计算失败: batch=%s error=%s", calc_batch_id, error)
            ctx.error_message = str(error)

        return ctx
