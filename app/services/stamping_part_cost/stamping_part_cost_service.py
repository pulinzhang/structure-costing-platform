"""
冲压零件价格核算服务

奇瑞核价口径（对齐工艺清单「单件」表 M/O/R 列）：
  M  blank_kg   = L × W × T × ρ_steel / 1e6 / parts_per_sheet
  O  scrap_kg   = M − part_weight
  N  util_%     = part_weight / M × 100

  R  原材料成本（单件）=
      ① M×(steel_ton/1000)×(1+λ)
    − ② M×λ×η×(scrap_ton/1000)
    − ③ O×η×(scrap_ton/1000)

  即：M×P×(1+λ) − M×λ×η×Q − O×η×Q（P/Q 为元/kg）
  unit_cost = R + process_fee

三项分列落库：material_amount_sheet / loss_scrap_deduction / process_scrap_deduction。
ρ_steel / λ / η 从系统配置读取；缺失时回退 7.85 / 0.003 / 0.97。
重量过程量不做中间四舍五入，与 Excel 公式结果一致。
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Optional

from sqlalchemy.exc import IntegrityError
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
from app.models.stamping import StampingPart
from app.models.stamping_part_cost_calc_log import StampingPartCostCalcLog
from app.models.stamping_scrap_price import StampingScrapPrice
from app.models.steel_price import SteelPrice
from app.repositories.stamping.scrap_price_repository import StampingScrapPriceRepository
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.repositories.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.repositories.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.steel_price.steel_price_repository import SteelPriceRepository
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostBatchApproveDTO,
    StampingPartCostBatchReverseAuditDTO,
    StampingPartCostCalcDTO,
    StampingPartCostDeleteDTO,
    StampingPartCostManualUnitCostDTO,
    StampingPartCostQuery,
    StampingPartCostScopeDTO,
)
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostBatchAuditResultVO,
    StampingPartCostBatchDeleteResultVO,
    StampingPartCostCalcLogVO,
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
    StampingPartCostFailedItemVO,
    StampingPartCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.settings.settings_service import SettingsService
from app.services.stamping_part_cost.helpers import (
    location_candidates,
    to_decimal,
)

logger = logging.getLogger("service.stamping_part_cost")

FORMULA_VERSION = "part-cost-v5"
AMOUNT_QUANTIZE = Decimal("0.000001")
UTIL_QUANTIZE = Decimal("0.01")
FEE_QUANTIZE = Decimal("0.001")

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STALE_PROCESSING_SECONDS = 2 * 60 * 60
DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/月份/基地/工厂正在计算中，请勿重复提交。"
SCOPE_REQUIRED_MESSAGE = "须选定年度、月份、基地、冲压工厂"

ProgressCallback = Callable[[int, str], None]


def _require_scope(dto: StampingPartCostScopeDTO) -> tuple[str, str]:
    location = (dto.location or "").strip()
    supplier = (dto.stamping_supplier or "").strip()
    if not dto.year or not dto.month or not location or not supplier:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    return location, supplier


def _quantize(value: Decimal, quant: Decimal) -> Decimal:
    return value.quantize(quant, rounding=ROUND_HALF_UP)


class DuplicateScopeCalcError(Exception):
    """同一计算范围已有进行中的任务。"""


class StampingPartCostService:
    """冲压零件价格核算业务逻辑。"""

    def __init__(self) -> None:
        self.cost_repo = StampingPartCostRepository()
        self.calc_log_repo = StampingPartCostCalcLogRepository()
        self.part_repo = StampingPartRepository()
        self.steel_repo = SteelPriceRepository()
        self.scrap_repo = StampingScrapPriceRepository()
        self.fee_repo = StampingProcessFeeRepository()
        self.settings_service = SettingsService()

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

            scrap = self._find_scrap_price(
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
        location, supplier = _require_scope(dto)
        self.calc_log_repo.ensure_processing_lock_index(db)
        self._expire_stale_processing(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"spc-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                {
                    "calc_batch_id": calc_batch_id,
                    "year": dto.year,
                    "month": dto.month,
                    "location": location,
                    "stamping_supplier": supplier,
                    "vehicle_model": dto.vehicle_model,
                    "version": dto.version,
                    "status": STATUS_PROCESSING,
                    "detail_text": "计算进行中...",
                    "started_at": started_at,
                    "operator_id": operator_id,
                    "operator_name": operator_name,
                    "created_by": operator_name,
                    "updated_by": operator_name,
                },
            )
            db.commit()
            db.refresh(record)
            return record
        except IntegrityError as error:
            db.rollback()
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE) from error

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_repo.update(
            db,
            log_id,
            {
                "status": STATUS_FAILED,
                "detail_text": detail_text,
                "finished_at": now(),
            },
        )
        db.commit()

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

        location, supplier = _require_scope(dto)
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

        scrap = self._find_scrap_price(
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

        upsert_rows: list[dict] = []
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

            row_or_error = self._calc_part_cost(
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
                    **self._part_snapshot(part),
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
                    **self._part_snapshot(part),
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

    def _find_scrap_price(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> StampingScrapPrice | None:
        for candidate in location_candidates(location):
            # 废料表通常存短名（芜湖）；优先短名
            short = candidate[:-2] if candidate.endswith("基地") else candidate
            record = self.scrap_repo.get_by_location_year_month(
                db, location=short, year=year, month=month
            )
            if record is not None:
                return record
            record = self.scrap_repo.get_by_location_year_month(
                db, location=candidate, year=year, month=month
            )
            if record is not None:
                return record
        return None

    def _find_steel_prices(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        grade: str,
        thickness: Decimal,
    ) -> list[SteelPrice]:
        rows: list[SteelPrice] = []
        for candidate in location_candidates(location):
            matched = self.steel_repo.list_by_grade_thickness(
                db,
                year=year,
                month=month,
                location=candidate,
                grade=grade,
                thickness=thickness,
            )
            if matched:
                rows.extend(matched)
                break
        return rows

    def _calc_part_cost(
        self,
        db: Session,
        *,
        part: StampingPart,
        year: int,
        month: int,
        supplier: str,
        scrap: StampingScrapPrice,
        scrap_ton_price: Decimal,
        density: Decimal,
        loss_rate: Decimal,
        recovery_rate: Decimal,
    ) -> dict | StampingPartCostFailedItemVO:
        material = (part.material or "").strip()
        if not material:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="材质为空，无法匹配钢材联动价",
            )

        sheet_length = to_decimal(part.sheet_length)
        sheet_width = to_decimal(part.sheet_width)
        thickness = to_decimal(part.thickness)
        part_weight = to_decimal(part.part_weight)
        parts_per_sheet = part.parts_per_sheet

        if (
            sheet_length is None
            or sheet_width is None
            or thickness is None
            or part_weight is None
            or parts_per_sheet is None
        ):
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="料片尺寸/料厚/单重/可制件数不完整",
            )
        if parts_per_sheet <= 0:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="可制件数必须大于 0",
            )

        # 对齐 Excel M：L×W×T×density/1e6/可制件数（不做中间四舍五入）
        blank_kg = (
            sheet_length * sheet_width * thickness * density
        ) / Decimal("1000000") / Decimal(parts_per_sheet)
        if blank_kg <= 0:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="预估单件材料消耗计算结果无效",
            )

        # Excel：O=M−H，N=H/M；finished 存净重 H
        finished_total_kg = part_weight
        scrap_kg = blank_kg - finished_total_kg
        utilization = _quantize(
            (finished_total_kg / blank_kg) * Decimal("100"), UTIL_QUANTIZE
        )

        steel_rows = self._find_steel_prices(
            db,
            year=year,
            month=month,
            location=part.location,
            grade=material,
            thickness=thickness,
        )
        if not steel_rows:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=f"未匹配到钢材联动价（材质={material}, 料厚={thickness}）",
            )
        if len(steel_rows) > 1:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason=(
                    f"钢材联动价匹配到 {len(steel_rows)} 条，"
                    "中标场景应唯一，请检查数据"
                ),
            )
        steel = steel_rows[0]
        if steel.final_price_per_ton is None:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="钢材联动价最终吨价为空",
            )
        steel_ton_price = Decimal(str(steel.final_price_per_ton))

        fee = self.fee_repo.get_by_business_key(
            db,
            year=year,
            location=part.location,
            stamping_supplier=supplier,
            vehicle_model=part.vehicle_model,
            version=part.version,
            part_number=part.part_number,
        )
        if fee is None:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="未找到对应加工费结果",
            )
        if fee.final_processing_fee is None:
            return StampingPartCostFailedItemVO(
                part_number=part.part_number,
                part_name=part.part_name,
                reason="加工费最终金额为空，请先完成加工费计算或手工调整",
            )
        process_fee_amount = _quantize(
            Decimal(str(fee.final_processing_fee)), FEE_QUANTIZE
        )

        # 对齐 Excel R 三项分列：
        # ① M×P×(1+λ)  ② M×λ×η×Q  ③ O×η×Q   （P/Q=元/kg=吨价/1000）
        kg_scale = Decimal("1000")
        steel_kg_price = steel_ton_price / kg_scale
        scrap_kg_price = scrap_ton_price / kg_scale
        material_amount_sheet = _quantize(
            blank_kg * steel_kg_price * (Decimal("1") + loss_rate),
            AMOUNT_QUANTIZE,
        )
        loss_scrap_deduction = _quantize(
            blank_kg * loss_rate * recovery_rate * scrap_kg_price,
            AMOUNT_QUANTIZE,
        )
        process_scrap_deduction = _quantize(
            scrap_kg * recovery_rate * scrap_kg_price,
            AMOUNT_QUANTIZE,
        )
        scrap_amount_sheet = _quantize(
            loss_scrap_deduction + process_scrap_deduction,
            AMOUNT_QUANTIZE,
        )
        material_net_per_part = _quantize(
            material_amount_sheet - loss_scrap_deduction - process_scrap_deduction,
            AMOUNT_QUANTIZE,
        )
        unit_cost = _quantize(
            material_net_per_part + process_fee_amount, AMOUNT_QUANTIZE
        )

        return {
            "density": density,
            "material_loss_rate": loss_rate,
            "scrap_recovery_rate": recovery_rate,
            "blank_weight_kg": blank_kg,
            "finished_total_kg": finished_total_kg,
            "scrap_weight_kg": scrap_kg,
            "material_utilization_pct": utilization,
            "steel_price_id": steel.id,
            "steel_mill": steel.steel_mill,
            "steel_ton_price": steel_ton_price,
            "scrap_price_id": scrap.id,
            "scrap_ton_price": scrap_ton_price,
            "process_fee_id": fee.id,
            "process_fee_amount": process_fee_amount,
            "material_amount_sheet": material_amount_sheet,
            "loss_scrap_deduction": loss_scrap_deduction,
            "process_scrap_deduction": process_scrap_deduction,
            "scrap_amount_sheet": scrap_amount_sheet,
            "material_net_per_part": material_net_per_part,
            "unit_cost": unit_cost,
        }

    @staticmethod
    def _part_snapshot(part: StampingPart) -> dict:
        return {
            "source_part_id": part.id,
            "seq_no": part.seq_no,
            "part_number": part.part_number,
            "part_name": part.part_name,
            "material": part.material,
            "thickness": part.thickness,
            "part_weight": part.part_weight,
            "sheet_length": part.sheet_length,
            "sheet_width": part.sheet_width,
            "parts_per_sheet": part.parts_per_sheet,
            "sheet_type": part.sheet_type,
            "die_type": part.die_type,
            "process_method": part.process_method,
            "automation": part.automation,
            "part_remark": part.remark,
            "sketch_url": part.sketch_url,
            "excel_filename": part.excel_filename,
            "excel_sheet_name": part.excel_sheet_name,
            "excel_row": part.excel_row,
            "excel_part_col": part.excel_part_col,
        }

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingPartCostCalcLogVO], int]:
        skip = (page - 1) * size
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            skip=skip,
            limit=size,
        )
        return [StampingPartCostCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> StampingPartCostCalcLogVO | None:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return None
        return StampingPartCostCalcLogVO.model_validate(record)

    def delete_calc_log(self, db: Session, log_id: int) -> bool:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return False
        if record.status == STATUS_PROCESSING:
            raise BusinessException("计算进行中，无法删除该记录")
        deleted = self.calc_log_repo.delete(db, log_id)
        if deleted:
            db.commit()
        return deleted

    def _expire_stale_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
    ) -> None:
        record = self.calc_log_repo.find_processing(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
        )
        if record is None or record.started_at is None:
            return
        if now() - record.started_at < timedelta(seconds=STALE_PROCESSING_SECONDS):
            return
        self.calc_log_repo.update(
            db,
            record.id,
            {
                "status": STATUS_FAILED,
                "detail_text": (record.detail_text or "")
                + "\n超时自动释放计算锁",
                "finished_at": now(),
            },
        )
        db.commit()

    def paginate(
        self, db: Session, query: StampingPartCostQuery
    ) -> tuple[list[StampingPartCostVO], int, dict]:
        skip = (query.page - 1) * query.size
        rows, total = self.cost_repo.paginate(
            db,
            year=query.year,
            month=query.month,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            skip=skip,
            limit=query.size,
        )
        filters = {
            "years": self.cost_repo.get_distinct_years(db),
            "months": self.cost_repo.get_distinct_months(db, year=query.year),
            "locations": self.cost_repo.get_distinct_locations(
                db, year=query.year, month=query.month
            ),
            "suppliers": self.cost_repo.get_distinct_suppliers(
                db,
                year=query.year,
                month=query.month,
                location=query.location,
            ),
            "summary": self.cost_repo.summarize_by_filters(
                db,
                year=query.year,
                month=query.month,
                location=query.location,
                stamping_supplier=query.stamping_supplier,
                vehicle_model=query.vehicle_model,
                version=query.version,
                part_number=query.part_number,
                audit_status=query.audit_status,
            ),
        }
        return (
            [StampingPartCostVO.model_validate(r) for r in rows],
            total,
            filters,
        )

    def get_by_id(self, db: Session, cost_id: int) -> StampingPartCostVO | None:
        record = self.cost_repo.get_by_id(db, cost_id)
        if record is None:
            return None
        return StampingPartCostVO.model_validate(record)

    def update_manual_unit_cost(
        self,
        db: Session,
        cost_id: int,
        dto: StampingPartCostManualUnitCostDTO,
        current_user: UserVO,
    ) -> StampingPartCostVO:
        """仅允许对计算失败且未审核的记录手工录入最终单件成本。"""
        record = self.cost_repo.get_by_id(db, cost_id)
        if not record:
            raise BusinessException(f"核算记录不存在: id={cost_id}")
        if record.calc_status != STATUS_FAILED:
            raise BusinessException("仅计算失败的记录允许手工改价")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再改价")

        remark = (dto.remark or "").strip()
        if not remark:
            raise BusinessException("备注不能为空")

        unit_cost = Decimal(str(dto.unit_cost)).quantize(
            AMOUNT_QUANTIZE, rounding=ROUND_HALF_UP
        )
        updated = self.cost_repo.update_fields(
            db,
            cost_id,
            {
                "unit_cost": unit_cost,
                "remark": remark,
                **audit_update(current_user),
            },
        )
        if not updated:
            raise BusinessException(f"核算记录不存在: id={cost_id}")
        return StampingPartCostVO.model_validate(updated)

    def list_years(self, db: Session) -> list[int]:
        years = set(self.cost_repo.get_distinct_years(db))
        years.update(self.steel_repo.list_distinct_years(db))
        return sorted(years, reverse=True)

    def list_locations(self, db: Session, year: int | None = None) -> list[str]:
        return self.cost_repo.get_distinct_locations(db, year=year)

    def list_suppliers(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        return self.cost_repo.get_distinct_suppliers(
            db, year=year, month=month, location=location
        )

    def batch_delete(
        self, db: Session, dto: StampingPartCostDeleteDTO
    ) -> StampingPartCostBatchDeleteResultVO:
        location, supplier = _require_scope(dto)
        skipped = self.cost_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_APPROVED],
        )
        deleted = self.cost_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
        db.commit()
        return StampingPartCostBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )

    def batch_approve(
        self,
        db: Session,
        dto: StampingPartCostBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingPartCostBatchAuditResultVO:
        location, supplier = _require_scope(dto)
        updated = self.cost_repo.approve_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            audited_by=display_name(current_user),
            audited_at=now(),
            audit_remark=dto.audit_remark,
            updated_by=display_name(current_user),
        )
        skipped = self.cost_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_APPROVED],
        ) - updated
        db.commit()
        return StampingPartCostBatchAuditResultVO(
            updated_count=updated,
            skipped_count=max(skipped, 0),
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingPartCostBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingPartCostBatchAuditResultVO:
        location, supplier = _require_scope(dto)
        updated = self.cost_repo.reverse_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
            reverse_audited_by=display_name(current_user),
            reverse_audited_at=now(),
            reverse_audit_remark=dto.reverse_audit_remark,
            updated_by=display_name(current_user),
        )
        db.commit()
        return StampingPartCostBatchAuditResultVO(
            updated_count=updated,
            skipped_count=0,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
