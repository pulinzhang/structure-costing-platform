"""
冲压加工费计算服务

公式：
- 单序加工费 = cost_ratio × price_per_stroke
- 零件加工费 = 各工序之和（保留 3 位小数）
- 「摆剪」工序不使用冲压设备，加工费固定为 0（不查吨位）

冲次费率匹配：年度相等 + 基地相等 + 吨位相等。

合并/双槽工艺（工艺方法含「合并」或「双槽」）缺吨位时：
- Excel 按顺序导入，上一零件为 id-1
- 表示与上一零件共模同冲（一次冲次出两种件）
- 须与上一零件基地相同，才可继承上一零件对应工序的吨位再计算
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping import StampingPart, StampingProcess
from app.models.stamping_process_fee_calc_log import StampingProcessFeeCalcLog
from app.repositories.stamping.stamping_process_fee_calc_log_repository import (
    StampingProcessFeeCalcLogRepository,
)
from app.repositories.stamping.stamping_process_fee_repository import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
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

ProgressCallback = Callable[[int, str], None]


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
        self.calc_log_repo.ensure_processing_lock_index(db)
        self._expire_stale_processing(
            db,
            year=dto.year,
            location=dto.location,
            stamping_supplier=dto.stamping_supplier,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            location=dto.location,
            stamping_supplier=dto.stamping_supplier,
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
                    "location": dto.location,
                    "stamping_supplier": dto.stamping_supplier,
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

        started_at = now()
        detail_lines: list[str] = [
            f"开始计算 year={dto.year} location={dto.location} "
            f"supplier={dto.stamping_supplier}"
        ]
        report(5, "加载冲次费率...")
        rates = self.tonnage_repo.list_by_location_year(db, dto.location, dto.year)
        if not rates:
            raise BusinessException(
                f"基地「{dto.location}」年度 {dto.year} 无冲次费率数据，请先维护冲次费率"
            )

        rate_map: dict[int, Decimal] = {
            int(r.tonnage): Decimal(str(r.price_per_stroke)) for r in rates
        }
        detail_lines.append(f"冲次费率 {len(rates)} 条")

        report(10, "加载冲压零件...")
        parts = self.part_repo.list_with_processes(
            db,
            location=dto.location,
            stamping_supplier=dto.stamping_supplier,
            vehicle_model=dto.vehicle_model,
            version=dto.version,
        )
        if not parts:
            raise BusinessException(
                f"基地「{dto.location}」工厂「{dto.stamping_supplier}」下未找到匹配的冲压零件"
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
                stamping_supplier=dto.stamping_supplier,
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
            else:
                processing_fee, process_count = fee_or_error
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
                "stamping_supplier": dto.stamping_supplier,
                "vehicle_model": part.vehicle_model,
                "version": part.version,
                **self._part_snapshot(part),
                "processing_fee": processing_fee,
                "process_count": process_count,
                "final_processing_fee": final_fee,
                "calc_fail_reason": calc_fail_reason,
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
            location=dto.location,
            stamping_supplier=dto.stamping_supplier,
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
            dto.location,
            dto.stamping_supplier,
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
    ) -> int | str:
        """
        解析工序吨位。
        缺吨位且工艺方法为合并/双槽时，继承上一零件(id-1)对应工序吨位；
        上一零件须与当前零件基地相同。
        成功返回 int；失败返回原因字符串。
        """
        if process.tonnage is not None:
            return int(process.tonnage)

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
        return int(matched.tonnage)

    def _calc_part_fee(
        self,
        db: Session,
        part: StampingPart,
        rate_map: dict[int, Decimal],
        year: int,
        prev_part_cache: dict[int, StampingPart | None],
    ) -> tuple[Decimal, int] | StampingProcessFeeFailedItemVO:
        processes = list(part.processes or [])
        if not processes:
            return self._build_failed_item(part, "无工序数据")

        total = Decimal("0")
        for process in sorted(processes, key=lambda p: (p.process_order or 0, p.id or 0)):
            # 摆剪不使用冲压设备，加工费固定为 0
            if self._is_swing_shear_process(process):
                logger.info(
                    "摆剪工序加工费计 0: part=%s process=%s",
                    part.part_number,
                    self._format_process_label(process),
                )
                continue

            tonnage_or_error = self._resolve_process_tonnage(
                db, part, process, prev_part_cache
            )
            if isinstance(tonnage_or_error, str):
                return self._build_failed_item(part, tonnage_or_error, process)

            tonnage = tonnage_or_error
            price = rate_map.get(tonnage)
            if price is None:
                process_label = self._format_process_label(process)
                location = (part.location or "").strip() or "(空)"
                return self._build_failed_item(
                    part,
                    f"当前工序 {process_label} 吨位 {tonnage}T "
                    f"在基地「{location}」{year} 年无冲次费率"
                    f"（须年度、基地、吨位均匹配）",
                    process,
                )

            cost_ratio = Decimal(
                str(process.cost_ratio if process.cost_ratio is not None else 1)
            )
            total += cost_ratio * price

        return total.quantize(FEE_QUANTIZE, rounding=ROUND_HALF_UP), len(processes)

    def paginate(
        self,
        db: Session,
        query: StampingProcessFeeQuery,
    ) -> tuple[list[StampingProcessFeeVO], int, dict]:
        skip = (query.page - 1) * query.size
        rows, total = self.fee_repo.paginate(
            db,
            year=query.year,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            skip=skip,
            limit=query.size,
        )
        vos = [StampingProcessFeeVO.model_validate(r) for r in rows]
        filters = {
            "year": query.year,
            "location": query.location,
            "stamping_supplier": query.stamping_supplier,
            "vehicle_model": query.vehicle_model,
            "version": query.version,
            "part_number": query.part_number,
            "audit_status": query.audit_status,
        }
        return vos, total, filters

    def batch_delete(
        self,
        db: Session,
        dto: StampingProcessFeeDeleteDTO,
    ) -> StampingProcessFeeBatchDeleteResultVO:
        location = dto.location.strip()
        supplier = dto.stamping_supplier.strip()
        if not location or not supplier:
            raise BusinessException("基地和冲压工厂不能为空")

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
        location = dto.location.strip()
        supplier = dto.stamping_supplier.strip()
        if not location or not supplier:
            raise BusinessException("基地和冲压工厂不能为空")
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
        location = dto.location.strip()
        supplier = dto.stamping_supplier.strip()
        if not location or not supplier:
            raise BusinessException("基地和冲压工厂不能为空")
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
            statuses=[AUDIT_PENDING, "rejected"],
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
