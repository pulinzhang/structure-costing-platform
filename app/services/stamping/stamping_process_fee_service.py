"""
冲压加工费计算服务

公式：
- 单序加工费 = cost_ratio × price_per_stroke
- 零件加工费 = 各工序之和（保留 3 位小数）
- 「摆剪」工序不使用冲压设备，加工费固定为 0（不查吨位）

冲次单价匹配：年度相等 + 基地相等 + 吨位相等。

合并/双槽工艺（工艺方法含「合并」或「双槽」）缺吨位时：
- Excel 按顺序导入，上一零件为 id-1
- 表示与上一零件共模同冲（一次冲次出两种件）
- 须与上一零件基地相同，才可继承上一零件对应工序的吨位再计算
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
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
from app.models.stamping import StampingPart, StampingProcess
from app.models.stamping_process_fee_calc_log import StampingProcessFeeCalcLog
from app.repositories.stamping.stamping_process_fee_calc_log_repository import (
    StampingProcessFeeCalcLogRepository,
)
from app.repositories.stamping.stamping_process_fee_repository import (
    PROCESS_ITEMS_KEY,
    StampingProcessFeeRepository,
)
from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.dto.stamping_process_fee_dto import (
    StampingProcessFeeBatchApproveDTO,
    StampingProcessFeeBatchReverseAuditDTO,
    StampingProcessFeeCalcDTO,
    StampingProcessFeeDeleteDTO,
    StampingProcessFeeQuery,
    StampingProcessFeeScopeDTO,
    StampingProcessFeeUpdateDTO,
)
from app.schemas.vo.stamping_process_fee_vo import (
    StampingProcessFeeBatchAuditResultVO,
    StampingProcessFeeBatchDeleteResultVO,
    StampingProcessFeeCalcLogVO,
    StampingProcessFeeCalcReadyVO,
    StampingProcessFeeCalcResultVO,
    StampingProcessFeeFailedItemVO,
    StampingProcessFeeVO,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.stamping")

FEE_QUANTIZE = Decimal("0.001")
STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STALE_PROCESSING_SECONDS = 2 * 60 * 60
DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/基地/工厂正在计算中，请勿重复提交。"
SCOPE_REQUIRED_MESSAGE = "须选定年度、基地、冲压工厂。"

ProgressCallback = Callable[[int, str], None]


def _require_scope(dto: StampingProcessFeeScopeDTO) -> tuple[str, str]:
    """规范化并校验范围字段（strip 后仍须齐全）。"""
    location = (dto.location or "").strip()
    supplier = (dto.stamping_supplier or "").strip()
    if not dto.year or not location or not supplier:
        raise BusinessException(SCOPE_REQUIRED_MESSAGE)
    return location, supplier


TONNAGE_SOURCE_SELF = "self"
TONNAGE_SOURCE_INHERITED = "inherited"
TONNAGE_SOURCE_SWING_SHEAR = "swing_shear"


@dataclass
class ProcessTonnageResolveResult:
    """工序吨位解析结果（成功时）"""

    tonnage: int
    source: str
    inherited_from_part_id: int | None = None
    inherited_from_part_number: str | None = None
    inherited_from_process_seq: str | None = None
    inherited_from_process_code: str | None = None


@dataclass
class TonnageRateInfo:
    """冲次单价快照"""

    price_per_stroke: Decimal
    tonnage_price_id: int | None = None


class DuplicateScopeCalcError(Exception):
    """同一计算范围已有进行中的任务。"""


class StampingProcessFeeService:
    """冲压加工费业务逻辑"""

    def __init__(self) -> None:
        self.fee_repo = StampingProcessFeeRepository()
        self.part_repo = StampingPartRepository()
        self.tonnage_repo = StampingTonnagePriceRepository()
        self.calc_log_repo = StampingProcessFeeCalcLogRepository()

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
        location, supplier = _require_scope(dto)
        self.calc_log_repo.ensure_processing_lock_index(db)
        self._expire_stale_processing(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"spf-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                {
                    "calc_batch_id": calc_batch_id,
                    "year": dto.year,
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

        location, supplier = _require_scope(dto)
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

            fee_or_error = self._calc_part_fee(
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

            final_fee = (
                manual_price if manual_price is not None else processing_fee
            )
            row = {
                "year": dto.year,
                "location": part.location,
                "stamping_supplier": supplier,
                "vehicle_model": part.vehicle_model,
                "version": part.version,
                **self._part_snapshot(part),
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
            detail_lines.append("提醒：存在计算价为 0 的零件，请到列表手工调整单价")
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
            self.calc_log_repo.update(
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
        skip = (page - 1) * size
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            skip=skip,
            limit=size,
        )
        return [StampingProcessFeeCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(self, db: Session, log_id: int) -> StampingProcessFeeCalcLogVO | None:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return None
        return StampingProcessFeeCalcLogVO.model_validate(record)

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
        location: str,
        stamping_supplier: str,
    ) -> None:
        record = self.calc_log_repo.find_processing(
            db,
            year=year,
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

    @staticmethod
    def _part_snapshot(part: StampingPart) -> dict:
        """从零件主表快照业务字段到加工费结果行。"""
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
        }

    @staticmethod
    def _resolve_final_fee(
        processing_fee: Decimal | float | None,
        manual_unit_price: Decimal | float | None,
    ) -> Decimal | None:
        """最终加工费：有手工调整单价则用手工，否则用系统计算值。"""
        if manual_unit_price is not None:
            return Decimal(str(manual_unit_price)).quantize(
                FEE_QUANTIZE, rounding=ROUND_HALF_UP
            )
        if processing_fee is None:
            return None
        return Decimal(str(processing_fee)).quantize(
            FEE_QUANTIZE, rounding=ROUND_HALF_UP
        )

    def update_manual_price(
        self,
        db: Session,
        fee_id: int,
        dto: StampingProcessFeeUpdateDTO,
        current_user: UserVO,
    ) -> StampingProcessFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise BusinessException(f"加工费记录不存在: id={fee_id}")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再调整")

        manual_price = None
        if dto.manual_unit_price is not None:
            manual_price = Decimal(str(dto.manual_unit_price)).quantize(
                FEE_QUANTIZE, rounding=ROUND_HALF_UP
            )

        final_fee = self._resolve_final_fee(record.processing_fee, manual_price)
        remark = (dto.remark or "").strip() or None
        updated = self.fee_repo.update_fields(
            db,
            fee_id,
            {
                "manual_unit_price": manual_price,
                "final_processing_fee": final_fee,
                "remark": remark,
                **audit_update(current_user),
            },
        )
        if not updated:
            raise BusinessException(f"加工费记录不存在: id={fee_id}")
        return StampingProcessFeeVO.model_validate(updated)

    def get_by_id(self, db: Session, fee_id: int) -> StampingProcessFeeVO | None:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            return None
        return StampingProcessFeeVO.model_validate(record)

    @staticmethod
    def _is_merged_process_method(process_method: str | None) -> bool:
        """工艺方法含「合并」或「双槽」：与上一零件共模同冲。"""
        if not process_method:
            return False
        text = str(process_method).strip()
        return "合并" in text or "双槽" in text

    @staticmethod
    def _is_swing_shear_process(process: StampingProcess) -> bool:
        """摆剪工序不使用冲压，加工费为 0。"""
        code = (process.process_code or "").strip()
        seq = (process.process_seq or "").strip()
        return "摆剪" in code or "摆剪" in seq

    @staticmethod
    def _format_process_method(process_method: str | None) -> str:
        """错误提示用：展示实际工艺方法文本。"""
        text = (process_method or "").strip()
        return text if text else "(空)"

    @staticmethod
    def _format_process_label(process: StampingProcess | None) -> str:
        """错误提示用：工序号 + 工序代码/名称。"""
        if process is None:
            return "?"
        seq = (process.process_seq or "").strip() or "?"
        code = (process.process_code or "").strip()
        if code:
            return f"{seq}/{code}"
        return seq

    @staticmethod
    def _summarize_processes(processes: list[StampingProcess]) -> str:
        """上一件工序清单，便于测试对照。"""
        if not processes:
            return "无工序"
        items: list[str] = []
        for process in sorted(
            processes, key=lambda p: (p.process_order or 0, p.id or 0)
        ):
            label = StampingProcessFeeService._format_process_label(process)
            if process.tonnage is None:
                tonnage_text = "无吨位"
            else:
                tonnage_text = f"{int(process.tonnage)}T"
            items.append(f"{label}={tonnage_text}")
        return "；".join(items)

    def _build_failed_item(
        self,
        part: StampingPart,
        reason: str,
        process: StampingProcess | None = None,
    ) -> StampingProcessFeeFailedItemVO:
        return StampingProcessFeeFailedItemVO(
            part_number=part.part_number,
            part_name=part.part_name,
            process_seq=(process.process_seq if process else None),
            process_code=(process.process_code if process else None),
            process_method=part.process_method,
            reason=reason,
        )

    def _get_previous_part(
        self,
        db: Session,
        part: StampingPart,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> StampingPart | None:
        """Excel 导入顺序下，上一零件为 id-1。"""
        if part.id is None or part.id <= 1:
            return None
        prev_id = part.id - 1
        if prev_id not in prev_part_cache:
            prev_part_cache[prev_id] = self.part_repo.get_by_id(db, prev_id)
        return prev_part_cache[prev_id]

    @staticmethod
    def _match_previous_process(
        process: StampingProcess,
        previous_processes: list[StampingProcess],
    ) -> StampingProcess | None:
        """按工序序号优先、其次工序顺序，匹配上一零件的对应工序。"""
        seq = (process.process_seq or "").strip()
        if seq:
            for prev in previous_processes:
                if (prev.process_seq or "").strip() == seq:
                    return prev
        order = process.process_order
        if order is not None:
            for prev in previous_processes:
                if prev.process_order == order:
                    return prev
        return None

    def _resolve_process_tonnage(
        self,
        db: Session,
        part: StampingPart,
        process: StampingProcess,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> ProcessTonnageResolveResult | str:
        """
        解析工序吨位。
        缺吨位且工艺方法为合并/双槽时，继承上一零件(id-1)对应工序吨位；
        上一零件须与当前零件基地相同。
        成功返回 ProcessTonnageResolveResult；失败返回原因字符串。
        """
        if process.tonnage is not None:
            return ProcessTonnageResolveResult(
                tonnage=int(process.tonnage),
                source=TONNAGE_SOURCE_SELF,
            )

        process_label = self._format_process_label(process)
        method_label = self._format_process_method(part.process_method)
        if not self._is_merged_process_method(part.process_method):
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"工艺方法「{method_label}」不可继承上一件吨位"
            )

        previous_part = self._get_previous_part(db, part, prev_part_cache)
        if previous_part is None:
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"工艺方法「{method_label}」应继承上一件，"
                f"但找不到上一零件(id-1)"
            )

        current_location = (part.location or "").strip()
        previous_location = (previous_part.location or "").strip()
        if not current_location or current_location != previous_location:
            prev_no = previous_part.part_number or str(previous_part.id)
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"工艺方法「{method_label}」应继承上一件，"
                f"但基地不一致（当前「{current_location or '(空)'}」，"
                f"上一件 {prev_no} 为「{previous_location or '(空)'}」），不可继承"
            )

        previous_processes = list(previous_part.processes or [])
        prev_summary = self._summarize_processes(previous_processes)
        prev_no = previous_part.part_number or str(previous_part.id)
        matched = self._match_previous_process(process, previous_processes)
        if matched is None:
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"工艺方法「{method_label}」应继承上一件 "
                f"{prev_no}(id={previous_part.id})，"
                f"但未匹配到对应工序。"
                f"上一件工序清单：{prev_summary}"
            )
        if matched.tonnage is None:
            matched_label = self._format_process_label(matched)
            return (
                f"当前工序 {process_label} 缺少吨位；"
                f"工艺方法「{method_label}」已匹配上一件 "
                f"{prev_no}(id={previous_part.id}) 工序 {matched_label}，"
                f"但该工序吨位为空。"
                f"上一件工序清单：{prev_summary}"
            )

        logger.info(
            "共模件继承吨位: part=%s location=%s method=%s process=%s "
            "from_part=%s from_process=%s tonnage=%s",
            part.part_number,
            current_location,
            method_label,
            process_label,
            previous_part.part_number,
            self._format_process_label(matched),
            matched.tonnage,
        )
        return ProcessTonnageResolveResult(
            tonnage=int(matched.tonnage),
            source=TONNAGE_SOURCE_INHERITED,
            inherited_from_part_id=previous_part.id,
            inherited_from_part_number=previous_part.part_number,
            inherited_from_process_seq=matched.process_seq,
            inherited_from_process_code=matched.process_code,
        )

    @staticmethod
    def _build_process_basis_text(
        *,
        process_label: str,
        tonnage_source: str,
        resolved_tonnage: int | None,
        cost_ratio: Decimal | None,
        price_per_stroke: Decimal | None,
        line_fee: Decimal,
        inherited_from_part_number: str | None = None,
        inherited_from_process_seq: str | None = None,
        inherited_from_process_code: str | None = None,
    ) -> str:
        """生成单道工序人可读计算依据。"""
        if tonnage_source == TONNAGE_SOURCE_SWING_SHEAR:
            return f"{process_label}: 摆剪不计费 = 0"

        ratio_text = (
            f"{cost_ratio:.2f}" if cost_ratio is not None else "1.00"
        )
        price_text = (
            f"{price_per_stroke:.3f}" if price_per_stroke is not None else "-"
        )
        fee_text = f"{line_fee:.3f}"
        tonnage_text = f"{resolved_tonnage}T" if resolved_tonnage is not None else "-"

        if tonnage_source == TONNAGE_SOURCE_INHERITED:
            from_seq = (inherited_from_process_seq or "").strip() or "?"
            from_code = (inherited_from_process_code or "").strip()
            from_label = f"{from_seq}/{from_code}" if from_code else from_seq
            from_part = inherited_from_part_number or "?"
            return (
                f"{process_label}: 继承上一件{from_part}/{from_label} "
                f"{tonnage_text} × 比例{ratio_text} × 单价{price_text} = {fee_text}"
            )

        return (
            f"{process_label}: 自有 {tonnage_text} × 比例{ratio_text} "
            f"× 单价{price_text} = {fee_text}"
        )

    def _calc_part_fee(
        self,
        db: Session,
        part: StampingPart,
        rate_map: dict[int, TonnageRateInfo],
        year: int,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> tuple[Decimal, int, list[dict]] | StampingProcessFeeFailedItemVO:
        processes = list(part.processes or [])
        if not processes:
            return self._build_failed_item(part, "无工序数据")

        total = Decimal("0")
        process_items: list[dict] = []
        for process in sorted(processes, key=lambda p: (p.process_order or 0, p.id or 0)):
            process_label = self._format_process_label(process)
            original_tonnage = (
                int(process.tonnage) if process.tonnage is not None else None
            )

            # 摆剪不使用冲压设备，加工费固定为 0
            if self._is_swing_shear_process(process):
                logger.info(
                    "摆剪工序加工费计 0: part=%s process=%s",
                    part.part_number,
                    process_label,
                )
                line_fee = Decimal("0").quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP)
                process_items.append(
                    {
                        "source_process_id": process.id,
                        "process_seq": process.process_seq,
                        "process_order": process.process_order,
                        "process_code": process.process_code,
                        "original_tonnage": original_tonnage,
                        "resolved_tonnage": None,
                        "tonnage_source": TONNAGE_SOURCE_SWING_SHEAR,
                        "inherited_from_part_id": None,
                        "inherited_from_part_number": None,
                        "inherited_from_process_seq": None,
                        "inherited_from_process_code": None,
                        "cost_ratio": None,
                        "tonnage_price_id": None,
                        "price_per_stroke": None,
                        "line_fee": line_fee,
                        "basis_text": self._build_process_basis_text(
                            process_label=process_label,
                            tonnage_source=TONNAGE_SOURCE_SWING_SHEAR,
                            resolved_tonnage=None,
                            cost_ratio=None,
                            price_per_stroke=None,
                            line_fee=line_fee,
                        ),
                        "remark": process.remark,
                    }
                )
                continue

            tonnage_or_error = self._resolve_process_tonnage(
                db, part, process, prev_part_cache
            )
            if isinstance(tonnage_or_error, str):
                return self._build_failed_item(part, tonnage_or_error, process)

            resolved = tonnage_or_error
            rate_info = rate_map.get(resolved.tonnage)
            if rate_info is None:
                location = (part.location or "").strip() or "(空)"
                return self._build_failed_item(
                    part,
                    f"当前工序 {process_label} 吨位 {resolved.tonnage}T "
                    f"在基地「{location}」{year} 年无冲次单价"
                    f"（须年度、基地、吨位均匹配）",
                    process,
                )

            cost_ratio = Decimal(
                str(process.cost_ratio if process.cost_ratio is not None else 1)
            )
            price = rate_info.price_per_stroke
            line_raw = cost_ratio * price
            line_fee = line_raw.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP)
            total += line_raw

            process_items.append(
                {
                    "source_process_id": process.id,
                    "process_seq": process.process_seq,
                    "process_order": process.process_order,
                    "process_code": process.process_code,
                    "original_tonnage": original_tonnage,
                    "resolved_tonnage": resolved.tonnage,
                    "tonnage_source": resolved.source,
                    "inherited_from_part_id": resolved.inherited_from_part_id,
                    "inherited_from_part_number": resolved.inherited_from_part_number,
                    "inherited_from_process_seq": resolved.inherited_from_process_seq,
                    "inherited_from_process_code": resolved.inherited_from_process_code,
                    "cost_ratio": cost_ratio,
                    "tonnage_price_id": rate_info.tonnage_price_id,
                    "price_per_stroke": price,
                    "line_fee": line_fee,
                    "basis_text": self._build_process_basis_text(
                        process_label=process_label,
                        tonnage_source=resolved.source,
                        resolved_tonnage=resolved.tonnage,
                        cost_ratio=cost_ratio,
                        price_per_stroke=price,
                        line_fee=line_fee,
                        inherited_from_part_number=resolved.inherited_from_part_number,
                        inherited_from_process_seq=resolved.inherited_from_process_seq,
                        inherited_from_process_code=resolved.inherited_from_process_code,
                    ),
                    "remark": process.remark,
                }
            )

        return (
            total.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP),
            len(processes),
            process_items,
        )

    def paginate(
        self,
        db: Session,
        query: StampingProcessFeeQuery,
    ) -> tuple[list[StampingProcessFeeVO], int, dict]:
        skip = (query.page - 1) * query.size
        filter_kwargs = dict(
            year=query.year,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            audit_status=query.audit_status,
        )
        rows, total = self.fee_repo.paginate(
            db,
            **filter_kwargs,
            only_zero=bool(query.only_zero),
            skip=skip,
            limit=query.size,
        )
        vos = [StampingProcessFeeVO.model_validate(r) for r in rows]
        # HUD 汇总不含 only_zero，避免点进待办筛选后大盘数字被掏空
        filters = {
            "year": query.year,
            "location": query.location,
            "stamping_supplier": query.stamping_supplier,
            "vehicle_model": query.vehicle_model,
            "version": query.version,
            "part_number": query.part_number,
            "audit_status": query.audit_status,
            "only_zero": bool(query.only_zero),
            "summary": self.fee_repo.summarize_by_filters(db, **filter_kwargs),
        }
        return vos, total, filters

    def batch_delete(
        self,
        db: Session,
        dto: StampingProcessFeeDeleteDTO,
    ) -> StampingProcessFeeBatchDeleteResultVO:
        location, supplier = _require_scope(dto)

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_APPROVED],
        )
        deleted = self.fee_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )
        db.commit()
        return StampingProcessFeeBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )

    def batch_approve(
        self,
        db: Session,
        dto: StampingProcessFeeBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingProcessFeeBatchAuditResultVO:
        location, supplier = _require_scope(dto)
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_APPROVED],
        )
        updated = self.fee_repo.approve_by_scope(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
            audited_by=operator,
            audited_at=now(),
            audit_remark=(dto.audit_remark or "").strip() or None,
            updated_by=operator,
        )
        db.commit()
        return StampingProcessFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingProcessFeeBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingProcessFeeBatchAuditResultVO:
        location, supplier = _require_scope(dto)
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
        )
        updated = self.fee_repo.reverse_by_scope(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
            reverse_audited_by=operator,
            reverse_audited_at=now(),
            reverse_audit_remark=remark,
            updated_by=operator,
        )
        db.commit()
        return StampingProcessFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )

    def list_years(self, db: Session) -> list[int]:
        fee_years = self.fee_repo.get_distinct_years(db)
        rate_years = self.tonnage_repo.get_distinct_years(db)
        return sorted(set(fee_years) | set(rate_years), reverse=True)

    def list_locations(self, db: Session, year: Optional[int] = None) -> list[str]:
        return self.fee_repo.get_distinct_locations(db, year=year)

    def list_suppliers(
        self,
        db: Session,
        year: Optional[int] = None,
        location: Optional[str] = None,
    ) -> list[str]:
        return self.fee_repo.get_distinct_suppliers(db, year=year, location=location)
