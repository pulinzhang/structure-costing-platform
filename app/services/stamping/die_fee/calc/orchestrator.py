"""冲压年度模具费计算编排。"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    AuditCreateFields,
    audit_create,
    display_name,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping.die import StampingDiePart
from app.repositories.stamping.die_fee_repository import StampingDieFeeRepository
from app.repositories.stamping.die_unit_price_repository import StampingDieUnitPriceRepository
from app.repositories.stamping.stamping_die_repository import StampingDiePartRepository
from app.schemas.dto.stamping_die_fee_dto import (
    DieFeeCalcLogPatch,
    DieFeeInsertPayload,
    DieFeeItemPayload,
    StampingDieFeeCalcDTO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.stamping_die_fee_vo import (
    StampingDieFeeCalcLogVO,
    StampingDieFeeCalcReadyVO,
    StampingDieFeeCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    TASK_TYPE_STAMPING_DIE_FEE_CALC,
    AsyncTaskService,
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.stamping.die_fee.calc.calc_log_service import DieFeeCalcLogService
from app.services.stamping.die_fee.calc.constants import (
    APPROVED_SCOPE_MESSAGE,
    STATUS_SUCCESS,
)
from app.services.stamping.die_fee.calc.part_calculator import DieFeePartCalculator
from app.services.stamping.die_fee.calc.weight_resolver import PreviousWeightIndex
from app.services.stamping.die_fee.fee_math import DieFeeLineResult, ZERO
from app.services.stamping.die.process_identity import matches_die_identity
from app.services.async_task.worker_runner import ProgressCallback

logger = logging.getLogger("service.stamping.die_fee.calc")


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _matches_part(
    part: StampingDiePart,
    *,
    stamping_supplier: str | None,
    version: str | None,
) -> bool:
    return matches_die_identity(
        part.stamping_supplier,
        part.version,
        stamping_supplier=stamping_supplier,
        version=version,
    )


def _parts_for_identity(
    parts: list[StampingDiePart],
    *,
    stamping_supplier: str | None,
    version: str | None,
) -> list[StampingDiePart]:
    return [
        part
        for part in parts
        if _matches_part(part, stamping_supplier=stamping_supplier, version=version)
    ]


class StampingDieFeeCalcOrchestrator:
    def __init__(self) -> None:
        self.fee_repo = StampingDieFeeRepository()
        self.die_repo = StampingDiePartRepository()
        self.unit_price_repo = StampingDieUnitPriceRepository()
        self.calc_log_service = DieFeeCalcLogService()
        self.part_calculator = DieFeePartCalculator()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> StampingDieFeeCalcReadyVO:
        supplier_filter = _strip_optional(stamping_supplier)
        version_filter = _strip_optional(version)
        has_unit_price = False
        calculable_count = 0
        part_count = 0
        if location and vehicle_model:
            all_parts = self.die_repo.list_with_processes(
                db, location=location, vehicle_model=vehicle_model
            )
            persist_parts = _parts_for_identity(
                all_parts,
                stamping_supplier=supplier_filter,
                version=version_filter,
            )
            part_count = len(persist_parts)
            price = self.unit_price_repo.get_effective(
                db, location=location, vehicle_model=vehicle_model
            )
            has_unit_price = (
                price is not None
                and price.allocation_qty is not None
                and price.allocation_qty > ZERO
            )
            previous_weights = PreviousWeightIndex()
            if has_unit_price and price is not None:
                for part in all_parts:
                    calculated, previous_weights = self.part_calculator.calc_part(
                        part,
                        steel_plate_unit_price=price.steel_plate_unit_price,
                        progressive_die_unit_price=price.progressive_die_unit_price,
                        allocation_qty=price.allocation_qty,
                        previous_weights=previous_weights,
                    )
                    if calculated is not None and _matches_part(
                        part,
                        stamping_supplier=supplier_filter,
                        version=version_filter,
                    ):
                        calculable_count += 1
        return StampingDieFeeCalcReadyVO(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=supplier_filter,
            version=version_filter,
            part_count=part_count,
            calculable_count=calculable_count,
            has_unit_price=has_unit_price,
        )

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
        version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingDieFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=_strip_optional(stamping_supplier),
            version=_strip_optional(version),
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> StampingDieFeeCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_service.mark_log_failed(db, log_id=log_id, detail_text=detail_text)

    def calculate(
        self,
        db: Session,
        dto: StampingDieFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingDieFeeCalcResultVO:
        def report(progress: int, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        started_at = now()
        supplier_filter = dto.stamping_supplier
        version_filter = dto.version
        identity_bits = [
            f"supplier={supplier_filter}" if supplier_filter else "",
            f"version={version_filter}" if version_filter else "",
        ]
        identity_label = " ".join(bit for bit in identity_bits if bit) or "全部供应商/版本"
        detail_lines: list[str] = [
            (
                f"开始计算 year={dto.year} location={dto.location} "
                f"vehicle={dto.vehicle_model} {identity_label}"
            )
        ]
        report(8, "加载模具布点...")
        parts = self.die_repo.list_with_processes(
            db, location=dto.location, vehicle_model=dto.vehicle_model
        )
        if not parts:
            raise BusinessException(f"基地「{dto.location}」项目「{dto.vehicle_model}」无模具布点")

        persist_parts = _parts_for_identity(
            parts,
            stamping_supplier=supplier_filter,
            version=version_filter,
        )
        if (supplier_filter or version_filter) and not persist_parts:
            raise BusinessException("所选供应商/版本下无模具布点")

        report(15, "加载模具单价...")
        price = self.unit_price_repo.get_effective(
            db, location=dto.location, vehicle_model=dto.vehicle_model
        )
        if price is None or price.allocation_qty <= ZERO:
            raise BusinessException(
                f"基地「{dto.location}」项目「{dto.vehicle_model}」无生效模具单价或分摊万台无效"
            )

        if self._count_approved(db, dto):
            raise BusinessException(APPROVED_SCOPE_MESSAGE, code=409)

        report(25, "清除未审核旧结果...")
        self.fee_repo.delete_all_by_scope(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            stamping_supplier=supplier_filter,
            version=version_filter,
        )

        audit = audit_create(current_user)
        success_count = 0
        skipped_no_die_count = 0
        total = len(parts)
        persist_total = len(persist_parts)
        previous_weights = PreviousWeightIndex()
        for index, part in enumerate(parts, start=1):
            calculated, previous_weights = self.part_calculator.calc_part(
                part,
                steel_plate_unit_price=price.steel_plate_unit_price,
                progressive_die_unit_price=price.progressive_die_unit_price,
                allocation_qty=price.allocation_qty,
                previous_weights=previous_weights,
            )
            if _matches_part(
                part,
                stamping_supplier=supplier_filter,
                version=version_filter,
            ):
                if calculated is None:
                    skipped_no_die_count += 1
                else:
                    self._insert_calculated_fee(
                        db,
                        dto=dto,
                        part=part,
                        calculated=calculated,
                        allocation_qty=price.allocation_qty,
                        audit=audit,
                    )
                    success_count += 1
            if index == total or index % 20 == 0:
                pct = 25 + int(65 * index / max(total, 1))
                report(pct, f"计算中 {index}/{total}...")

        detail_lines.append(f"布点（本批落库范围）{persist_total} 件，共模扫描 {total} 件")
        detail_lines.append(
            f"入库 {success_count}，跳过（无模具信息或系统费≤0）{skipped_no_die_count}"
        )
        finished_at = now()
        result = StampingDieFeeCalcResultVO(
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            stamping_supplier=supplier_filter,
            version=version_filter,
            calc_batch_id=calc_batch_id,
            log_id=log_id,
            status=STATUS_SUCCESS,
            total_parts=persist_total,
            success_count=success_count,
            skipped_no_die_count=skipped_no_die_count,
            failed_count=0,
            detail_text="\n".join(detail_lines),
            started_at=started_at.isoformat(timespec="seconds"),
            finished_at=finished_at.isoformat(timespec="seconds"),
        )
        if log_id is not None:
            self.calc_log_service.calc_log_repo.update(
                db,
                log_id,
                DieFeeCalcLogPatch(
                    status=STATUS_SUCCESS,
                    total_parts=result.total_parts,
                    success_count=result.success_count,
                    skipped_no_die_count=result.skipped_no_die_count,
                    failed_count=0,
                    detail_text=result.detail_text,
                    finished_at=finished_at,
                    updated_by=display_name(current_user) or None,
                ),
            )
        db.commit()
        report(100, "计算完成")
        logger.info(
            "年度模具费计算完成: year=%s location=%s vehicle=%s success=%s skipped=%s",
            dto.year,
            dto.location,
            dto.vehicle_model,
            success_count,
            skipped_no_die_count,
        )
        return result

    def _count_approved(self, db: Session, dto: StampingDieFeeCalcDTO) -> int:
        return self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            statuses=[AUDIT_APPROVED],
            stamping_supplier=dto.stamping_supplier,
            version=dto.version,
        )

    def _insert_calculated_fee(
        self,
        db: Session,
        *,
        dto: StampingDieFeeCalcDTO,
        part: StampingDiePart,
        calculated: tuple[Decimal, str, Decimal, list[DieFeeLineResult]],
        allocation_qty: Decimal,
        audit: AuditCreateFields,
    ) -> None:
        die_fee, price_kind, unit_price, lines = calculated
        self.fee_repo.insert_with_items(
            db,
            DieFeeInsertPayload(
                year=dto.year,
                location=part.location,
                vehicle_model=part.vehicle_model,
                stamping_supplier=part.stamping_supplier,
                version=part.version,
                part_number=part.part_number,
                source_die_part_id=part.id,
                seq_no=part.seq_no,
                part_name=part.part_name,
                material=part.material,
                thickness=part.thickness,
                part_weight=part.part_weight,
                die_type=part.die_type,
                die_method=part.die_method,
                production_mode=part.production_mode,
                part_grade=part.part_grade,
                excel_filename=part.excel_filename,
                price_kind=price_kind,
                unit_price=unit_price,
                allocation_qty=allocation_qty,
                die_fee=die_fee,
                adjustment_amount=None,
                final_die_fee=die_fee,
                audit_status=AUDIT_PENDING,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
                items=[
                    DieFeeItemPayload(
                        source_die_process_id=line.source_die_process_id,
                        process_seq=line.process_seq,
                        process_order=line.process_order,
                        process_code=line.process_code,
                        estimated_weight_t=line.estimated_weight_t,
                        alloc_ratio=line.alloc_ratio,
                        die_sets=line.die_sets,
                        unit_price=unit_price,
                        allocation_qty=allocation_qty,
                        price_kind=price_kind,
                        line_die_fee=line.line_die_fee,
                        basis_text=line.basis_text,
                    )
                    for line in lines
                ],
            ),
        )

    def start_calc(
        self,
        db: Session,
        dto: StampingDieFeeCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        if self._count_approved(db, dto):
            raise BusinessException(APPROVED_SCOPE_MESSAGE, code=409)

        lock_log = self.calc_log_service.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STAMPING_DIE_FEE_CALC,
            message="已提交计算队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            result = self.calculate(
                worker_db,
                dto,
                current_user=current_user,
                progress_callback=on_progress,
                log_id=log_id,
                calc_batch_id=calc_batch_id,
            )
            label = calc_status_label(result.status)
            return outcome_from_calc_status(
                result.status,
                failed_message=f"计算失败：入库 {result.success_count}，跳过 {result.skipped_no_die_count}",
                completed_message=(
                    f"计算{label}：入库 {result.success_count}，"
                    f"跳过 {result.skipped_no_die_count}"
                ),
                result=result.model_dump(),
            )

        def on_crash(worker_db: Session, error: BaseException) -> None:
            self.mark_log_failed(
                worker_db,
                log_id=log_id,
                detail_text=f"计算失败: {error}",
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始计算...",
            work=work,
            on_crash=on_crash,
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)
