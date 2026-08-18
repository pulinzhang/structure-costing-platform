"""
冲压零件价格核算编排器（串联就绪检查 / 单件计算 / 落库 / 日志）

计算链：
  1. get_calc_ready / PriceResolver — 前置数据
  2. PartCostCalculator             — 单零件核价
  3. cost_repo.bulk_upsert          — 结果落库
  4. PartCostCalcLogService         — 计算锁与过程日志
"""

from __future__ import annotations

from typing import Any


import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    AUDIT_REJECTED,
    audit_create,
    audit_update,
    display_name,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.costing import StampingPartCostCalcLog
from app.repositories.costing.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
    StampingPartCostFailedItemVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.calc.calc_log_service import (
    PartCostCalcLogService,
)
from app.services.costing.stamping_part_cost.calc.constants import (
    FORMULA_VERSION,
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
)
from app.services.costing.stamping_part_cost.calc.models import ProgressCallback
from app.services.costing.stamping_part_cost.calc.part_calculator import (
    PartCostCalculator,
    part_snapshot,
)
from app.services.costing.stamping_part_cost.calc.resolvers import PriceResolver
from app.services.costing.stamping_part_cost.calc.scope import require_scope
from app.services.costing.stamping_part_cost.helpers import location_candidates
from app.services.settings.system.settings_service import SettingsService

logger = logging.getLogger("service.stamping_part_cost.calc")


class StampingPartCostCalcOrchestrator:
    """冲压零件价格核算编排器。"""

    def __init__(self) -> None:
        self.cost_repo = StampingPartCostRepository()
        self.calc_log_repo = StampingPartCostCalcLogRepository()
        self.part_repo = StampingPartRepository()
        self.steel_repo = SteelPriceRepository()
        self.scrap_repo = StampingScrapPriceRepository()
        self.fee_repo = StampingProcessFeeRepository()
        self.settings_service = SettingsService()
        self.price_resolver = PriceResolver(
            steel_repo=self.steel_repo,
            scrap_repo=self.scrap_repo,
        )
        self.part_calculator = PartCostCalculator(
            price_resolver=self.price_resolver,
            fee_repo=self.fee_repo,
        )
        self.calc_log_service = PartCostCalcLogService(
            calc_log_repo=self.calc_log_repo,
        )

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> StampingPartCostCalcReadyVO:
        location_value = (location or "").strip() or None
        supplier_value = (stamping_supplier or "").strip() or None

        part_count = 0
        if location_value and supplier_value:
            parts = self.part_repo.list_with_processes(
                db,
                location=location_value,
                stamping_supplier=supplier_value,
                vehicle_model=vehicle_model,
                version=version,
            )
            part_count = len(parts)

        steel_price_count = 0
        scrap_price_count = 0
        process_fee_count = 0

        if year and month and location_value:
            for candidate in location_candidates(location_value):
                count = self.steel_repo.count_by_year_month_location(
                    db, year=year, month=month, location=candidate
                )
                if count > steel_price_count:
                    steel_price_count = count

            scrap = self.price_resolver.find_scrap_price(
                db, location=location_value, year=year, month=month
            )
            scrap_price_count = 1 if scrap is not None else 0

        if year and location_value and supplier_value:
            process_fee_count = self.fee_repo.count_by_scope_and_statuses(
                db,
                year=year,
                location=location_value,
                stamping_supplier=supplier_value,
                statuses=[AUDIT_PENDING, AUDIT_APPROVED, AUDIT_REJECTED],
            )

        can_calculate = bool(
            year
            and month
            and location_value
            and supplier_value
            and part_count > 0
            and steel_price_count > 0
            and scrap_price_count > 0
            and process_fee_count > 0
        )

        return StampingPartCostCalcReadyVO(
            year=year,
            month=month,
            location=location_value,
            stamping_supplier=supplier_value,
            vehicle_model=vehicle_model,
            version=version,
            part_count=part_count,
            steel_price_count=steel_price_count,
            scrap_price_count=scrap_price_count,
            process_fee_count=process_fee_count,
            can_calculate=can_calculate,
        )

    def begin_processing(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingPartCostCalcLog:
        return self.calc_log_service.begin_processing(
            db,
            dto,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_service.mark_log_failed(
            db, log_id=log_id, detail_text=detail_text
        )

    def calculate(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingPartCostCalcResultVO:
        def report(progress: int, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        location, supplier = require_scope(dto)
        density = self.settings_service.get_steel_density(db)
        loss_rate = self.settings_service.get_material_loss_rate(db)
        recovery_rate = self.settings_service.get_scrap_recovery_rate(db)
        started_at = now()
        detail_lines: list[str] = [
            f"开始计算 year={dto.year} month={dto.month} location={location} "
            f"supplier={supplier} density={density} loss_rate={loss_rate} "
            f"recovery={recovery_rate} formula={FORMULA_VERSION}"
        ]

        report(5, "校验前置数据...")
        ready = self.get_calc_ready(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            vehicle_model=dto.vehicle_model,
            version=dto.version,
        )
        if not ready.can_calculate:
            raise BusinessException(
                "前置数据未齐：须同时具备钢材联动价、废料月度价、加工费结果与匹配零件"
            )
        detail_lines.append(
            f"就绪：零件 {ready.part_count}，钢材价 {ready.steel_price_count}，"
            f"废料价 {ready.scrap_price_count}，加工费 {ready.process_fee_count}"
        )

        scrap = self.price_resolver.find_scrap_price(
            db, location=location, year=dto.year, month=dto.month
        )
        if scrap is None:
            raise BusinessException(
                f"基地「{location}」{dto.year}-{dto.month:02d} 无废料月度销售价"
            )
        scrap_ton_price = Decimal(str(scrap.net_price))
        detail_lines.append(
            f"废料净价 {scrap_ton_price} 元/吨 (id={scrap.id}, location={scrap.location})"
        )

        report(10, "加载冲压零件...")
        parts = self.part_repo.list_with_processes(
            db,
            location=location,
            stamping_supplier=supplier,
            vehicle_model=dto.vehicle_model,
            version=dto.version,
        )
        if not parts:
            raise BusinessException(
                f"基地「{location}」工厂「{supplier}」下未找到匹配的冲压零件"
            )
        detail_lines.append(f"匹配零件 {len(parts)} 件")

        upsert_rows: list[dict[str, Any]] = []
        failed_items: list[StampingPartCostFailedItemVO] = []
        success_count = 0
        skipped_approved_count = 0
        audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        total = len(parts)
        calculated_at = now()

        for index, part in enumerate(parts, start=1):
            existing = self.cost_repo.get_by_business_key(
                db,
                year=dto.year,
                month=dto.month,
                location=part.location,
                stamping_supplier=supplier,
                vehicle_model=part.vehicle_model,
                version=part.version,
                part_number=part.part_number,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                skipped_approved_count += 1
                continue

            row_or_error = self.part_calculator.calc_part_cost(
                db,
                part=part,
                year=dto.year,
                month=dto.month,
                supplier=supplier,
                scrap=scrap,
                scrap_ton_price=scrap_ton_price,
                density=density,
                loss_rate=loss_rate,
                recovery_rate=recovery_rate,
            )

            if isinstance(row_or_error, StampingPartCostFailedItemVO):
                failed_items.append(row_or_error)
                row = {
                    "year": dto.year,
                    "month": dto.month,
                    "location": part.location,
                    "stamping_supplier": supplier,
                    "vehicle_model": part.vehicle_model,
                    "version": part.version,
                    **part_snapshot(part),
                    "density": density,
                    "material_loss_rate": loss_rate,
                    "scrap_recovery_rate": recovery_rate,
                    "calc_batch_id": calc_batch_id,
                    "calc_status": STATUS_FAILED,
                    "calc_fail_reason": row_or_error.reason,
                    "formula_version": FORMULA_VERSION,
                    "calculated_at": calculated_at,
                    "unit_cost": None,
                    "audit_status": AUDIT_PENDING,
                }
            else:
                success_count += 1
                row = {
                    "year": dto.year,
                    "month": dto.month,
                    "location": part.location,
                    "stamping_supplier": supplier,
                    "vehicle_model": part.vehicle_model,
                    "version": part.version,
                    **part_snapshot(part),
                    **row_or_error,
                    "calc_batch_id": calc_batch_id,
                    "calc_status": STATUS_SUCCESS,
                    "calc_fail_reason": None,
                    "formula_version": FORMULA_VERSION,
                    "calculated_at": calculated_at,
                    "audit_status": AUDIT_PENDING,
                }

            if existing:
                row.update(update_audit)
            else:
                row.update(audit)
            upsert_rows.append(row)

            if index == total or index % 20 == 0:
                pct = 10 + int(80 * index / max(total, 1))
                report(pct, f"计算中 {index}/{total}...")

        report(92, "写入核算结果...")
        if upsert_rows:
            self.cost_repo.bulk_upsert(db, upsert_rows)

        if failed_items and success_count:
            status = STATUS_PARTIAL
        elif failed_items and not success_count:
            status = STATUS_FAILED
        else:
            status = STATUS_SUCCESS

        detail_lines.append(
            f"成功 {success_count}，失败 {len(failed_items)}，"
            f"跳过已审 {skipped_approved_count}"
        )
        for item in failed_items[:20]:
            detail_lines.append(f"失败 {item.part_number}: {item.reason}")

        finished_at = now()
        result = StampingPartCostCalcResultVO(
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            vehicle_model=dto.vehicle_model,
            version=dto.version,
            calc_batch_id=calc_batch_id,
            log_id=log_id,
            status=status,
            total_parts=len(parts),
            success_count=success_count,
            failed_count=len(failed_items),
            skipped_approved_count=skipped_approved_count,
            failed_items=failed_items[:50],
            detail_text="\n".join(detail_lines),
            started_at=started_at.isoformat(timespec="seconds"),
            finished_at=finished_at.isoformat(timespec="seconds"),
        )

        if log_id is not None:
            self.calc_log_repo.update(
                db,
                log_id,
                {
                    "status": status,
                    "total_parts": result.total_parts,
                    "success_count": result.success_count,
                    "failed_count": result.failed_count,
                    "skipped_approved_count": result.skipped_approved_count,
                    "detail_text": result.detail_text,
                    "finished_at": finished_at,
                    "updated_by": display_name(current_user) or None,
                },
            )
            db.commit()

        report(100, "计算完成")
        logger.info(
            "零件价格核算完成: year=%s month=%s location=%s supplier=%s "
            "success=%s failed=%s skipped_approved=%s",
            dto.year,
            dto.month,
            location,
            supplier,
            result.success_count,
            result.failed_count,
            result.skipped_approved_count,
        )
        return result
