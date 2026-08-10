"""
钢价计算编排器

计算链：
  1. 取出材料厚度列表（冲压件）
  2. 根据基价表补齐钢厂 / 大类 / 基准价 / 加工费 / 溯源
  3. 根据加减价政策补齐厚/宽调整
  4. 调用 SteelPriceService 落库
  5. 写入计算批次日志（detail_text 记录全过程，含错误）
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.steel_price import SteelPriceCalcLogRepository
from app.schemas.dto.steel_price_policy_dto import GradeType, PolicyMatchRequest, PolicyType
from app.services.stamping.stamping_service import StampingPartService
from app.services.steel_base_price.steel_base_price_service import SteelBasePriceService
from app.services.steel_price.calc.models import (
    CalcRow,
    MaterialThicknessRow,
    ProcessLogBuilder,
    SteelPriceCalcRequest,
    SteelPriceCalcResult,
)
from app.services.steel_price.steel_price_service import FORMULA_VERSION, SteelPriceService
from app.services.steel_price_policy.steel_price_policy_service import SteelPricePolicyService
from app.repositories.steel_price_policy import SteelPricePolicyRepository


logger = logging.getLogger("service.steel_price.calc")

# detail_text 中逐条列出的无基价 / 行级警告上限，超出则摘要
_DETAIL_ITEM_LIMIT = 200


class SteelPriceCalcOrchestrator:
    """钢材价格计算编排器。"""

    def __init__(self) -> None:
        self.stamping_service = StampingPartService()
        self.base_price_service = SteelBasePriceService()
        self.policy_service = SteelPricePolicyService()
        self.policy_repository = SteelPricePolicyRepository()
        self.steel_price_service = SteelPriceService()
        self.calc_log_repository = SteelPriceCalcLogRepository()

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
            materials = self._load_material_thickness_list(db, normalized)
            result.material_count = len(materials)
            log_builder.line(f"去重材料+厚度规格: {result.material_count} 条")
            if result.material_count == 0:
                log_builder.warn("未取到任何材料厚度规格，后续无法产出结果行")

            # Step 2
            log_builder.section("Step2 基价表补齐")
            rows, no_base_count, no_base_details = self._enrich_with_base_price(
                db, normalized, materials
            )
            result.enriched_count = len(rows)
            result.no_base_count = no_base_count
            log_builder.line(f"命中基价并展开: {result.enriched_count} 行")
            log_builder.line(f"无基价/基价不完整: {result.no_base_count} 条")
            self._append_limited_details(
                log_builder, "无基价明细", no_base_details, is_error=True
            )

            # Step 3
            log_builder.section("Step3 加减价匹配")
            rows = self._apply_adjustments(db, normalized, rows)
            match_stats = self._summarize_match_status(rows)
            for key, count in match_stats.items():
                log_builder.line(f"match_status={key}: {count}")
            row_warnings = [
                f"{r.grade} {float(r.thickness):.4f}*{float(r.width):.2f} "
                f"[{r.match_status}] {r.calc_message}"
                for r in rows
                if r.messages
            ]
            self._append_limited_details(
                log_builder, "行级警告/未命中", row_warnings, is_error=True
            )

            # Step 4
            log_builder.section("Step4 结果落库")
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

            result.status = self._resolve_batch_status(result, rows)
            log_builder.section("计算结束")
            log_builder.line(f"批次状态: {result.status}")

        except Exception as error:
            result.status = "failed"
            log_builder.section("计算异常")
            log_builder.error(str(error))
            log_builder.line(traceback.format_exc())
            logger.exception("钢价计算失败: batch=%s error=%s", calc_batch_id, error)
            # 仍落库日志后再向上抛/返回；此处返回 failed 结果，由 Router 决定是否 4xx/5xx
            finished_at = datetime.now()
            result.finished_at = finished_at.isoformat(timespec="seconds")
            result.detail_text = log_builder.build()
            result.log_id = self._persist_calc_log(
                db,
                result=result,
                started_at=started_at,
                finished_at=finished_at,
            )
            raise

        finished_at = datetime.now()
        result.finished_at = finished_at.isoformat(timespec="seconds")
        log_builder.line(f"结束时间: {result.finished_at}")
        log_builder.line(
            f"耗时: {(finished_at - started_at).total_seconds():.2f}s"
        )
        result.detail_text = log_builder.build()
        result.log_id = self._persist_calc_log(
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
    ) -> tuple[list, int]:
        """分页查询计算历史。"""
        from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO

        skip = (page - 1) * size
        records, total = self.calc_log_repository.paginate(
            db,
            year=year,
            month=month,
            location=location.strip() if location else None,
            skip=skip,
            limit=size,
        )
        return [SteelPriceCalcLogVO.model_validate(r) for r in records], total

    def get_log(self, db: Session, log_id: int):
        from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO

        record = self.calc_log_repository.get_by_id(db, log_id)
        if record is None:
            return None
        return SteelPriceCalcLogVO.model_validate(record)

    def _persist_calc_log(
        self,
        db: Session,
        *,
        result: SteelPriceCalcResult,
        started_at: datetime,
        finished_at: datetime,
    ) -> int | None:
        if result.year is None or result.month is None:
            logger.error(
                "写入计算日志失败: batch=%s 缺少 year/month", result.calc_batch_id
            )
            return None
        try:
            record = self.calc_log_repository.create(
                db,
                {
                    "calc_batch_id": result.calc_batch_id,
                    "year": int(result.year),
                    "month": int(result.month),
                    "location": result.location or "",
                    "stamping_supplier": result.stamping_supplier,
                    "vehicle_model": result.vehicle_model,
                    "status": result.status,
                    "material_count": result.material_count,
                    "enriched_count": result.enriched_count,
                    "no_base_count": result.no_base_count,
                    "created_count": result.created_count,
                    "updated_count": result.updated_count,
                    "skipped_approved_count": result.skipped_approved_count,
                    "failed_count": result.failed_count,
                    "detail_text": result.detail_text or "",
                    "started_at": started_at,
                    "finished_at": finished_at,
                },
            )
            db.commit()
            db.refresh(record)
            return record.id
        except Exception as error:
            db.rollback()
            logger.exception(
                "写入计算日志失败: batch=%s error=%s", result.calc_batch_id, error
            )
            return None

    @staticmethod
    def _resolve_batch_status(result: SteelPriceCalcResult, rows: list[CalcRow]) -> str:
        if result.failed_count > 0:
            return "partial"
        if result.material_count == 0:
            return "failed"
        if result.enriched_count == 0:
            return "failed"
        if result.no_base_count > 0:
            return "partial"
        if any(r.calc_status != "success" for r in rows):
            return "partial"
        if result.created_count + result.updated_count == 0 and result.skipped_approved_count == 0:
            return "failed"
        return "success"

    @staticmethod
    def _summarize_match_status(rows: list[CalcRow]) -> dict[str, int]:
        stats: dict[str, int] = {}
        for row in rows:
            stats[row.match_status] = stats.get(row.match_status, 0) + 1
        return dict(sorted(stats.items()))

    @staticmethod
    def _append_limited_details(
        log_builder: ProcessLogBuilder,
        title: str,
        items: list[str],
        *,
        is_error: bool,
    ) -> None:
        if not items:
            return
        log_builder.line(f"{title}（共 {len(items)} 条，最多展示 {_DETAIL_ITEM_LIMIT}）:")
        shown = items[:_DETAIL_ITEM_LIMIT]
        for item in shown:
            if is_error:
                log_builder.error(item)
            else:
                log_builder.line(f"  - {item}")
        omitted = len(items) - len(shown)
        if omitted > 0:
            log_builder.warn(f"另有 {omitted} 条未展开")

    # ------------------------------------------------------------------
    # Step 1
    # ------------------------------------------------------------------

    def _load_material_thickness_list(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
    ) -> list[MaterialThicknessRow]:
        """取出材料厚度列表。"""
        raw_rows = self.stamping_service.list_material_specs(
            db,
            location=request.location,
            stamping_supplier=request.stamping_supplier,
            vehicle_model=request.vehicle_model,
        )
        result: list[MaterialThicknessRow] = []
        for row in raw_rows:
            material = (row.get("material") or "").strip()
            thickness = row.get("thickness")
            if not material or thickness is None:
                continue
            result.append(
                MaterialThicknessRow(
                    material=material,
                    thickness=Decimal(str(thickness)),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Step 2
    # ------------------------------------------------------------------

    def _enrich_with_base_price(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        materials: list[MaterialThicknessRow],
    ) -> tuple[list[CalcRow], int, list[str]]:
        """
        根据基价表更新更多信息。

        匹配键：year + month + location + grade(=material)
        同一牌号可对应多条基价（不同钢厂/规格）→ 展开为多行。
        """
        assert request.location is not None

        base_records = self.base_price_service.list_for_calc(
            db,
            year=request.year,
            month=request.month,
            location=request.location,
        )
        grade_index: dict[str, list] = {}
        for record in base_records:
            key = (record.grade or "").strip()
            if not key:
                continue
            grade_index.setdefault(key, []).append(record)

        rows: list[CalcRow] = []
        no_base_count = 0
        no_base_details: list[str] = []

        for material in materials:
            matches = grade_index.get(material.material, [])
            if not matches:
                no_base_count += 1
                no_base_details.append(
                    f"{material.material}@{float(material.thickness):.4f} 无匹配基价"
                )
                continue

            for base in matches:
                if base.width is None or base.thick is None or base.base_price is None:
                    no_base_count += 1
                    no_base_details.append(
                        f"{material.material}@{float(material.thickness):.4f} "
                        f"基价字段不完整(id={base.id})"
                    )
                    continue

                row = CalcRow(
                    year=request.year,
                    month=request.month,
                    location=request.location,
                    grade=material.material,
                    thickness=material.thickness,
                    steel_mill=base.steel_mill,
                    category_name=base.category_name,
                    width=Decimal(str(base.width)),
                    base_thickness=Decimal(str(base.thick)),
                    base_price=Decimal(str(base.base_price)),
                    processing_fee=Decimal(str(base.processing_fee or 0)),
                    base_price_id=base.id,
                    base_excel_filename=base.excel_filename,
                    base_sheet_name=base.sheet_name,
                    base_excel_row=base.excel_row,
                    base_excel_col=base.excel_col,
                    match_status="base_only",
                    calc_status="partial",
                )
                rows.append(row)

        return rows, no_base_count, no_base_details

    # ------------------------------------------------------------------
    # Step 3
    # ------------------------------------------------------------------

    def _apply_adjustments(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        rows: list[CalcRow],
    ) -> list[CalcRow]:
        """根据加减价政策更新厚度/宽度调整额及溯源。"""
        for row in rows:
            self._apply_thickness_adjustment(db, request, row)
            self._apply_width_adjustment(db, request, row)
            row.finalize_status()
        return rows

    def _apply_thickness_adjustment(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        row: CalcRow,
    ) -> None:
        if not row.steel_mill or not row.category_name or row.base_thickness is None:
            row.add_message("缺少基价维度，无法匹配厚度加减价")
            return

        match_req = PolicyMatchRequest(
            year=request.year,
            month=request.month,
            steel_mill=row.steel_mill,
            category_name=row.category_name,
            policy_type=PolicyType.THICKNESS,
            grade_type=GradeType.GRADE,
            grade_value=row.grade,
            base_thickness=row.base_thickness,
            thickness=row.thickness,
            width=row.width,
        )
        result = self.policy_service.match(db, match_req)
        if not result.matched or result.item is None or result.policy_id is None:
            row.add_message("未命中厚度加减价政策")
            return

        row.thickness_adjustment = Decimal(str(result.price_adjustment or 0))
        row.thickness_policy_id = result.policy_id
        row.thickness_ladder_item_id = result.item.id
        self._fill_policy_provenance(
            db,
            policy_id=result.policy_id,
            item_id=result.item.id,
            prefix="thickness",
            row=row,
        )

    def _apply_width_adjustment(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        row: CalcRow,
    ) -> None:
        if not row.steel_mill or not row.category_name or row.width is None:
            row.add_message("缺少基价维度，无法匹配宽度加减价")
            return

        match_req = PolicyMatchRequest(
            year=request.year,
            month=request.month,
            steel_mill=row.steel_mill,
            category_name=row.category_name,
            policy_type=PolicyType.WIDTH,
            grade_type=GradeType.GRADE,
            grade_value=row.grade,
            base_thickness=None,
            thickness=row.thickness,
            width=row.width,
        )
        result = self.policy_service.match(db, match_req)
        if not result.matched or result.item is None or result.policy_id is None:
            fallback_req = PolicyMatchRequest(
                year=request.year,
                month=request.month,
                steel_mill=row.steel_mill,
                category_name=row.category_name,
                policy_type=PolicyType.WIDTH,
                grade_type=GradeType.CATEGORY,
                grade_value=row.category_name,
                base_thickness=None,
                thickness=row.thickness,
                width=row.width,
            )
            result = self.policy_service.match(db, fallback_req)

        if not result.matched or result.item is None or result.policy_id is None:
            row.add_message("未命中宽度加减价政策")
            return

        row.width_adjustment = Decimal(str(result.price_adjustment or 0))
        row.width_policy_id = result.policy_id
        row.width_ladder_item_id = result.item.id
        self._fill_policy_provenance(
            db,
            policy_id=result.policy_id,
            item_id=result.item.id,
            prefix="width",
            row=row,
        )

    def _fill_policy_provenance(
        self,
        db: Session,
        *,
        policy_id: int,
        item_id: int,
        prefix: str,
        row: CalcRow,
    ) -> None:
        """从政策主表/阶梯明细冗余写入 Excel 溯源四件套。"""
        policy = self.policy_repository.get_by_id(db, policy_id, load_items=False)
        item = self.policy_repository.get_item_by_id(db, item_id)
        if policy is not None:
            setattr(row, f"{prefix}_excel_filename", policy.excel_filename)
        if item is not None:
            setattr(row, f"{prefix}_excel_row", item.excel_row)
            setattr(row, f"{prefix}_excel_col", item.excel_col)
