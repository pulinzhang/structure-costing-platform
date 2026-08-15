"""
冲压加工费计算服务（编排）

公式：
- 单序加工费 = cost_ratio × price_per_stroke
- 零件加工费 = 各工序之和（保留 3 位小数）
- 「摆剪」工序不使用冲压设备，加工费固定为 0（不查吨位）
- 共模件对应工序若上一件为摆剪，同样计 0

冲次单价匹配：年度相等 + 基地相等 + 吨位相等。

合并/双槽/共用工艺缺吨位时（零件工艺方法，或任一道工序代码含「合并」/「双槽」/「共用」，
如工序代码「左右合并」「双槽」）：
- Excel 按顺序导入，上一零件为 id-1
- 表示与上一零件共模同冲（一次冲次出两种件）
- 须与上一零件基地相同，才可继承上一零件对应工序的吨位再计算
- 若上一件对应工序为摆剪，则本工序同样按摆剪计 0
- 工序数量以上一件为准；当前多出的工序视为录入错误，跳过不计费
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, audit_update
from app.common.audit import display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping import StampingPart
from app.models.stamping_process_fee_calc_log import StampingProcessFeeCalcLog
from app.repositories.stamping.stamping_process_fee_repository import (
    PROCESS_ITEMS_KEY,
    StampingProcessFeeRepository,
)
from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.schemas.vo.stamping_process_fee_vo import (
    StampingProcessFeeCalcLogVO,
    StampingProcessFeeCalcReadyVO,
    StampingProcessFeeCalcResultVO,
    StampingProcessFeeFailedItemVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.process_fee.calc.calc_log_service import (
    ProcessFeeCalcLogService,
)
from app.services.stamping.process_fee.calc.constants import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
)
from app.services.stamping.process_fee.calc.models import (
    ProgressCallback,
    TonnageRateInfo,
)
from app.services.stamping.process_fee.calc.part_calculator import PartFeeCalculator
from app.services.stamping.process_fee.calc.snapshot import part_snapshot
from app.services.stamping.process_fee.fee_math import resolve_final_fee
from app.services.stamping.process_fee.scope import require_scope

logger = logging.getLogger("service.stamping.process_fee.calc")


class StampingProcessFeeCalcService:
    """冲压加工费计算编排：就绪检查、并发锁、批量计算、计算日志。"""

    def __init__(self) -> None:
        self.fee_repo = StampingProcessFeeRepository()
        self.part_repo = StampingPartRepository()
        self.tonnage_repo = StampingTonnagePriceRepository()
        self.calc_log_service = ProcessFeeCalcLogService()
        self.part_calculator = PartFeeCalculator()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> StampingProcessFeeCalcReadyVO:
        if location:
            rates = self.tonnage_repo.list_by_location_year(db, location, year)
        else:
            rates = self.tonnage_repo.list_by_year(db, year)
        parts = []
        if location and stamping_supplier:
            parts = self.part_repo.list_with_processes(
                db,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
        return StampingProcessFeeCalcReadyVO(
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_count=len(parts),
            tonnage_rate_count=len(rates),
        )

    def begin_processing(
        self,
        db: Session,
        dto: StampingProcessFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingProcessFeeCalcLog:
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

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingProcessFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            page=page,
            size=size,
        )

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> StampingProcessFeeCalcLogVO | None:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> bool:
        return self.calc_log_service.delete_calc_log(db, log_id)

    def calculate(
        self,
        db: Session,
        dto: StampingProcessFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingProcessFeeCalcResultVO:
        def report(progress: int, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        location, supplier = require_scope(dto)
        started_at = now()
        detail_lines: list[str] = [
            f"开始计算 year={dto.year} location={location} "
            f"supplier={supplier}"
        ]
        report(5, "加载冲次单价...")
        rates = self.tonnage_repo.list_by_location_year(db, location, dto.year)
        if not rates:
            raise BusinessException(
                f"基地「{location}」年度 {dto.year} 无冲次单价数据，请先维护冲次单价"
            )

        rate_map: dict[int, TonnageRateInfo] = {
            int(r.tonnage): TonnageRateInfo(
                price_per_stroke=Decimal(str(r.price_per_stroke)),
                tonnage_price_id=r.id,
            )
            for r in rates
        }
        detail_lines.append(f"冲次单价 {len(rates)} 条")

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

        prev_part_cache: dict[int, StampingPart | None] = {}
        upsert_rows: list[dict] = []
        failed_items: list[StampingProcessFeeFailedItemVO] = []
        zero_fee_items: list[StampingProcessFeeFailedItemVO] = []
        success_count = 0
        zero_fee_count = 0
        skipped_approved_count = 0
        audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        total = len(parts)

        for index, part in enumerate(parts, start=1):
            existing = self.fee_repo.get_by_business_key(
                db,
                year=dto.year,
                location=part.location,
                stamping_supplier=supplier,
                vehicle_model=part.vehicle_model,
                version=part.version,
                part_number=part.part_number,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                skipped_approved_count += 1
                continue

            fee_or_error = self.part_calculator.calc_part_fee(
                db, part, rate_map, dto.year, prev_part_cache
            )
            manual_price = existing.manual_unit_price if existing else None

            if isinstance(fee_or_error, StampingProcessFeeFailedItemVO):
                failed_items.append(fee_or_error)
                processing_fee = None
                process_count = len(part.processes or [])
                calc_fail_reason = fee_or_error.reason
                process_items: list[dict] = []
            else:
                processing_fee, process_count, process_items = fee_or_error
                calc_fail_reason = None
                success_count += 1
                if processing_fee is not None and Decimal(str(processing_fee)) == 0:
                    zero_fee_count += 1
                    if len(zero_fee_items) < 50:
                        zero_fee_items.append(
                            StampingProcessFeeFailedItemVO(
                                part_number=part.part_number,
                                part_name=part.part_name,
                                process_seq=None,
                                process_code=None,
                                process_method=None,
                                reason="系统计算加工费为 0，请到列表手工调整单价",
                            )
                        )

            final_fee = resolve_final_fee(processing_fee, manual_price)
            row = {
                "year": dto.year,
                "location": part.location,
                "stamping_supplier": supplier,
                "vehicle_model": part.vehicle_model,
                "version": part.version,
                **part_snapshot(part),
                "processing_fee": processing_fee,
                "process_count": process_count,
                "final_processing_fee": final_fee,
                "calc_fail_reason": calc_fail_reason,
                "audit_status": AUDIT_PENDING,
                PROCESS_ITEMS_KEY: process_items,
            }
            if existing:
                row.update(update_audit)
            else:
                row.update(audit)
            upsert_rows.append(row)

            if index == total or index % 20 == 0:
                pct = 10 + int(80 * index / max(total, 1))
                report(pct, f"计算中 {index}/{total}...")

        report(92, "写入加工费结果...")
        if upsert_rows:
            self.fee_repo.bulk_upsert(db, upsert_rows)

        if failed_items and success_count:
            status = STATUS_PARTIAL
        elif failed_items and not success_count:
            status = STATUS_FAILED
        else:
            status = STATUS_SUCCESS

        detail_lines.append(
            f"成功 {success_count}，失败 {len(failed_items)}，"
            f"零价 {zero_fee_count}，跳过已审 {skipped_approved_count}"
        )
        if zero_fee_count:
            detail_lines.append(
                "提醒：存在计算价为 0 的零件，请到列表手工调整单价"
            )
        for item in failed_items[:20]:
            detail_lines.append(
                f"失败 {item.part_number} {item.process_seq or ''}: {item.reason}"
            )

        finished_at = now()
        result = StampingProcessFeeCalcResultVO(
            year=dto.year,
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
            zero_fee_count=zero_fee_count,
            skipped_approved_count=skipped_approved_count,
            failed_items=failed_items[:50],
            zero_fee_items=zero_fee_items,
            detail_text="\n".join(detail_lines),
            started_at=started_at.isoformat(timespec="seconds"),
            finished_at=finished_at.isoformat(timespec="seconds"),
        )

        if log_id is not None:
            self.calc_log_service.calc_log_repo.update(
                db,
                log_id,
                {
                    "status": status,
                    "total_parts": result.total_parts,
                    "success_count": result.success_count,
                    "failed_count": result.failed_count,
                    "zero_fee_count": result.zero_fee_count,
                    "skipped_approved_count": result.skipped_approved_count,
                    "detail_text": result.detail_text,
                    "finished_at": finished_at,
                    "updated_by": display_name(current_user) or None,
                },
            )
            db.commit()

        report(100, "计算完成")
        logger.info(
            "冲压加工费计算完成: year=%s location=%s supplier=%s "
            "success=%s failed=%s zero_fee=%s skipped_approved=%s",
            dto.year,
            location,
            supplier,
            result.success_count,
            result.failed_count,
            result.zero_fee_count,
            result.skipped_approved_count,
        )
        return result
