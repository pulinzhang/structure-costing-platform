"""
BOM 焊接费计算编排器

输入：
  - L0 焊接工艺拆解节点（含明细）
  - 基地+年度焊接单价

公式（单 L0）：
  计费用量 = 辅助量（有则用之）否则过程量
  再按单价单位换算（长度 mm↔cm；面积 平方≡m2/平方米）
  line_fee = 计费用量 × unit_price（Q4；不乘装配用量）
  total_l0_welding_fee = Σ line_fee
  final_l0_welding_fee = total_l0_welding_fee + other_fee（重算保留已录入其它费用）

已审核结果跳过覆盖；不要求上游拆解已审核。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from decimal import Decimal
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, audit_update, display_name
from app.exceptions.base import BusinessException
from app.common.bom.welding_billing_qty import resolve_billing_qty_for_price
from app.common.money import Q4, quantize_money
from app.common.timezone import now
from app.services.bom.l0_welding_fee.fee_math import resolve_final_l0_welding_fee
from app.models.bom import BomL0WeldingFeeCalcLog, BomWeldingProcessBreakdownNode
from app.models.bom.welding_unit_price import BomWeldingUnitPrice
from app.repositories.bom.l0_welding_fee_repository import BomL0WeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.repositories.bom.welding_unit_price_repository import (
    BomWeldingUnitPriceRepository,
)
from app.schemas.dto.bom_l0_welding_fee_dto import (
    BomL0WeldingFeeCalcDTO,
    BomL0WeldingFeeItemPayload,
    BomL0WeldingFeeUpsertPayload,
)
from app.schemas.vo.bom_l0_welding_fee_vo import (
    BomL0WeldingFeeCalcLogVO,
    BomL0WeldingFeeCalcReadyVO,
    BomL0WeldingFeeCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.services.async_task import (
    TASK_TYPE_BOM_L0_WELDING_FEE_CALC,
    AsyncTaskService,
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.bom.l0_welding_fee.calc.calc_log_service import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    BomL0WeldingFeeCalcLogService,
)

logger = logging.getLogger("service.bom.l0_welding_fee.calc")

ProgressCallback = Callable[[int, str], None]

MATCH_MATCHED = "matched"
MATCH_MISSING_PRICE = "missing_price"
MATCH_UNMAPPED = "unmapped"

CALC_OK = "ok"
CALC_PARTIAL = "partial"
CALC_FAILED = "failed"

MAP_READY = "ready"


@dataclass(slots=True)
class _L0FeeCalcParts:
    process_line_count: int
    matched_line_count: int
    missing_price_count: int
    total_l0_welding_fee: Decimal
    calc_status: str
    calc_message: str | None
    items: list[BomL0WeldingFeeItemPayload]


class BomL0WeldingFeeCalcOrchestrator:
    """焊接费计算编排器。"""

    def __init__(self) -> None:
        self.fee_repo = BomL0WeldingFeeRepository()
        self.breakdown_repo = BomWeldingProcessBreakdownRepository()
        self.unit_price_repo = BomWeldingUnitPriceRepository()
        self.calc_log_service = BomL0WeldingFeeCalcLogService()

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomL0WeldingFeeCalcReadyVO:
        location = location.strip()
        vehicle_model = vehicle_model.strip()
        bom_version = bom_version.strip()
        prices = self.unit_price_repo.list_by_location_year(db, location, year)
        l0_count = self.breakdown_repo.count_by_filters(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            level=0,
        )
        l0_process_line_total = self.breakdown_repo.sum_process_line_count_by_filters(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            level=0,
        )
        zero_process_l0_count = self.breakdown_repo.count_by_filters(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            level=0,
            process_line_count_eq=0,
        )
        return BomL0WeldingFeeCalcReadyVO(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            l0_count=l0_count,
            unit_price_count=len(prices),
            l0_process_line_total=l0_process_line_total,
            zero_process_l0_count=zero_process_l0_count,
        )

    def begin_processing(
        self,
        db: Session,
        dto: BomL0WeldingFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> BomL0WeldingFeeCalcLog:
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
        self.calc_log_service.mark_failed(db, log_id=log_id, detail_text=detail_text)

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BomL0WeldingFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> BomL0WeldingFeeCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def calculate(
        self,
        db: Session,
        dto: BomL0WeldingFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> BomL0WeldingFeeCalcResultVO:
        def report(progress: int, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        year = dto.year
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        started_at = now()
        detail_lines: list[str] = [
            f"开始计算 year={year} location={location} "
            f"vehicle={vehicle_model} bom_version={bom_version}"
        ]

        report(5, "加载焊接单价...")
        prices = self.unit_price_repo.list_by_location_year(db, location, year)
        if not prices:
            raise BusinessException(
                f"基地「{location}」年度 {year} 无焊接单价数据，请先维护焊接单价"
            )
        price_map: dict[str, BomWeldingUnitPrice] = {p.item_name: p for p in prices}
        detail_lines.append(f"焊接单价 {len(prices)} 条")

        report(10, "加载成品焊接工艺拆解...")
        all_nodes = self.breakdown_repo.list_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        l0_nodes = [n for n in all_nodes if n.level == 0]
        if not l0_nodes:
            raise BusinessException(
                f"基地「{location}」车型「{vehicle_model}」版本「{bom_version}」"
                f"下未找到成品焊接工艺拆解"
            )
        detail_lines.append(f"成品节点 {len(l0_nodes)} 个")

        upsert_rows: list[BomL0WeldingFeeUpsertPayload] = []
        skipped_approved_count = 0
        failed_count = 0
        missing_price_total = 0
        audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        total = len(l0_nodes)

        for index, node in enumerate(l0_nodes, start=1):
            existing = self.fee_repo.get_by_business_key(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                source_breakdown_node_id=node.id,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                skipped_approved_count += 1
                continue

            parts = self._calc_l0_fee(node, price_map)
            missing_price_total += parts.missing_price_count
            if parts.calc_status == CALC_FAILED:
                failed_count += 1

            other_fee = existing.other_fee if existing else None
            final_fee = resolve_final_l0_welding_fee(
                parts.total_l0_welding_fee,
                other_fee,
            )

            upsert_rows.append(
                BomL0WeldingFeeUpsertPayload(
                    year=year,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    source_breakdown_node_id=node.id,
                    part_number=node.part_number,
                    part_name=node.part_name,
                    customer_name=node.customer_name,
                    weld_info_raw=(node.weld_info_raw or "").strip() or None,
                    process_line_count=parts.process_line_count,
                    matched_line_count=parts.matched_line_count,
                    missing_price_count=parts.missing_price_count,
                    total_l0_welding_fee=parts.total_l0_welding_fee,
                    final_l0_welding_fee=final_fee,
                    calc_batch_id=calc_batch_id,
                    calc_status=parts.calc_status,
                    calc_message=parts.calc_message,
                    audit_status=AUDIT_PENDING,
                    updated_by=(update_audit["updated_by"] if existing else audit["updated_by"]),
                    created_by=None if existing else audit["created_by"],
                    items=parts.items,
                )
            )

            if index == total or index % 20 == 0:
                pct = 10 + int(80 * index / max(total, 1))
                report(pct, f"计算中 {index}/{total}...")

        report(92, "写入焊接费结果...")
        created_count = 0
        updated_count = 0
        if upsert_rows:
            _, created_count, updated_count = self.fee_repo.bulk_upsert(db, upsert_rows)

        if failed_count and (created_count + updated_count - failed_count) > 0:
            status = STATUS_PARTIAL
        elif failed_count and (created_count + updated_count) == failed_count:
            status = STATUS_FAILED
        elif missing_price_total and (created_count + updated_count):
            status = STATUS_PARTIAL
        else:
            status = STATUS_SUCCESS

        detail_lines.append(
            f"新增 {created_count}，更新 {updated_count}，"
            f"失败 {failed_count}，缺单价明细 {missing_price_total}，"
            f"跳过已审 {skipped_approved_count}"
        )

        finished_at = now()
        result = BomL0WeldingFeeCalcResultVO(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            calc_batch_id=calc_batch_id,
            log_id=log_id,
            status=status,
            l0_count=len(l0_nodes),
            created_count=created_count,
            updated_count=updated_count,
            skipped_approved_count=skipped_approved_count,
            failed_count=failed_count,
            missing_price_count=missing_price_total,
            detail_text="\n".join(detail_lines),
            started_at=started_at.isoformat(timespec="seconds"),
            finished_at=finished_at.isoformat(timespec="seconds"),
        )

        if log_id is not None:
            self.calc_log_service.finalize(
                db,
                log_id=log_id,
                data={
                    "status": status,
                    "l0_count": result.l0_count,
                    "created_count": result.created_count,
                    "updated_count": result.updated_count,
                    "skipped_approved_count": result.skipped_approved_count,
                    "failed_count": result.failed_count,
                    "missing_price_count": result.missing_price_count,
                    "detail_text": result.detail_text,
                    "finished_at": finished_at,
                    "updated_by": display_name(current_user) or None,
                },
            )
        else:
            db.commit()
            self.calc_log_service.persist(
                db,
                result=result,
                operator_name=display_name(current_user) or "系统",
            )

        report(100, "计算完成")
        logger.info(
            "焊接费计算完成: year=%s location=%s vehicle=%s version=%s "
            "created=%s updated=%s failed=%s skipped=%s missing_price=%s",
            year,
            location,
            vehicle_model,
            bom_version,
            created_count,
            updated_count,
            failed_count,
            skipped_approved_count,
            missing_price_total,
        )
        return result

    def start_calc(
        self,
        db: Session,
        dto: BomL0WeldingFeeCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        lock_log = self.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        scoped = BomL0WeldingFeeCalcDTO(
            year=dto.year,
            location=dto.location.strip(),
            vehicle_model=dto.vehicle_model.strip(),
            bom_version=dto.bom_version.strip(),
        )
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_BOM_L0_WELDING_FEE_CALC,
            message="已提交计算队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            result = self.calculate(
                worker_db,
                scoped,
                current_user,
                progress_callback=on_progress,
                log_id=log_id,
                calc_batch_id=calc_batch_id,
            )
            label = calc_status_label(result.status)
            return outcome_from_calc_status(
                result.status,
                failed_message=(
                    f"计算失败：新增 {result.created_count}，更新 {result.updated_count}，"
                    f"失败 {result.failed_count}"
                ),
                completed_message=(
                    f"计算{label}：新增 {result.created_count}，"
                    f"更新 {result.updated_count}，失败 {result.failed_count}，"
                    f"缺单价 {result.missing_price_count}"
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

    def _calc_l0_fee(
        self,
        node: BomWeldingProcessBreakdownNode,
        price_map: dict[str, BomWeldingUnitPrice],
    ) -> _L0FeeCalcParts:
        lines = list(node.lines or [])
        items: list[BomL0WeldingFeeItemPayload] = []
        matched_count = 0
        missing_count = 0
        total_fee = Decimal("0")

        for line in lines:
            item = BomL0WeldingFeeItemPayload(
                line_no=line.line_no,
                process_token=line.process_token,
                standard_process_name=line.standard_process_name,
                process_qty=quantize_money(line.process_qty, Q4),
                process_qty_unit=line.process_qty_unit,
                unit_price=None,
                unit=None,
                line_fee=None,
                match_status=MATCH_UNMAPPED,
                source_breakdown_line_id=line.id,
                remark=None,
            )

            name = (line.standard_process_name or "").strip()
            is_ready = (line.map_status or "") == MAP_READY and bool(name)
            if not is_ready:
                if not name:
                    item.remark = "未映射标准工艺"
                else:
                    item.remark = f"映射未就绪({line.map_status})"
                items.append(item)
                continue

            price_row = price_map.get(name)
            if price_row is None:
                item.match_status = MATCH_MISSING_PRICE
                item.remark = f"未找到单价：{name}"
                missing_count += 1
                items.append(item)
                continue

            try:
                billing_qty, billing_unit, billing_remark = resolve_billing_qty_for_price(
                    line,
                    price_unit=price_row.unit,
                )
            except ValueError as error:
                item.match_status = MATCH_UNMAPPED
                item.remark = str(error)
                items.append(item)
                continue

            unit_price = quantize_money(price_row.unit_price, Q4)
            line_fee = quantize_money(billing_qty * unit_price, Q4)
            item.process_qty = billing_qty
            item.process_qty_unit = billing_unit
            item.unit_price = unit_price
            item.unit = price_row.unit
            item.line_fee = line_fee
            item.match_status = MATCH_MATCHED
            item.remark = billing_remark
            matched_count += 1
            total_fee += line_fee
            items.append(item)

        process_line_count = len(lines)
        total_fee = quantize_money(total_fee, Q4)

        if process_line_count == 0:
            calc_status = CALC_FAILED
            calc_message = "无焊接工艺明细"
        elif missing_count == 0 and matched_count > 0:
            calc_status = CALC_OK
            calc_message = None
        elif matched_count > 0 and missing_count > 0:
            calc_status = CALC_PARTIAL
            calc_message = f"部分缺单价（匹配 {matched_count}，缺价 {missing_count}）"
        elif missing_count > 0 and matched_count == 0:
            calc_status = CALC_FAILED
            calc_message = f"全部缺单价（{missing_count} 行）"
        else:
            calc_status = CALC_FAILED
            calc_message = "无可用标准工艺映射"

        return _L0FeeCalcParts(
            process_line_count=process_line_count,
            matched_line_count=matched_count,
            missing_price_count=missing_count,
            total_l0_welding_fee=total_fee,
            calc_status=calc_status,
            calc_message=calc_message,
            items=items,
        )
