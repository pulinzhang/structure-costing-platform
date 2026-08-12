"""钢材价格业务服务。"""

import logging
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update, display_name
from app.common.timezone import now
from app.repositories.steel_price import SteelPriceRepository
from app.schemas.dto.steel_price_dto import (
    SteelPriceAuditDTO,
    SteelPriceBatchApproveDTO,
    SteelPriceBatchDeleteDTO,
    SteelPriceBatchReverseAuditDTO,
    SteelPriceCreate,
    SteelPriceQuery,
    SteelPriceReverseAuditDTO,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceBatchAuditResultVO,
    SteelPriceBatchDeleteResultVO,
    SteelPriceFilterOptions,
    SteelPriceResponse,
)
from app.schemas.vo.user_vo import UserVO


logger = logging.getLogger("service.steel_price")

AUDIT_PENDING = "pending"
AUDIT_APPROVED = "approved"
AUDIT_REJECTED = "rejected"
FORMULA_VERSION = "v1"


class SteelPriceService:
    """钢材价格查询、手工维护与审核业务。"""

    def __init__(self) -> None:
        self.repository = SteelPriceRepository()

    @staticmethod
    def _compute_final_price(
        *,
        base_price: float | Decimal,
        thickness_adjustment: float | Decimal,
        width_adjustment: float | Decimal,
        zinc_adjustment: float | Decimal,
        processing_fee: float | Decimal,
        other_adjustment: float | Decimal,
    ) -> Decimal:
        return (
            Decimal(str(base_price))
            + Decimal(str(thickness_adjustment))
            + Decimal(str(width_adjustment))
            + Decimal(str(zinc_adjustment))
            + Decimal(str(processing_fee))
            + Decimal(str(other_adjustment))
        )

    @staticmethod
    def _build_spec(thickness: float, width: float, spec: str | None) -> str | None:
        if spec and spec.strip():
            return spec.strip()
        return f"{thickness:.2f}*{width:.2f}"

    def _ensure_not_approved(self, record) -> Optional[str]:
        if record.audit_status == AUDIT_APPROVED:
            return "记录已审核通过，请先反审核后再修改/删除/重算"
        return None

    def paginate(
        self, db: Session, query: SteelPriceQuery
    ) -> tuple[list[SteelPriceResponse], int, SteelPriceFilterOptions]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            year=query.year,
            month=query.month,
            location=query.location.strip() if query.location else None,
            category_name=query.category_name.strip() if query.category_name else None,
            grade=query.grade.strip() if query.grade else None,
            steel_mill=query.steel_mill.strip() if query.steel_mill else None,
            audit_status=query.audit_status.strip() if query.audit_status else None,
            skip=skip,
            limit=query.size,
        )
        rows = [SteelPriceResponse.model_validate(record) for record in records]
        filters = SteelPriceFilterOptions.model_validate(self.repository.get_filter_options(db))
        return rows, total, filters

    def get_by_id(self, db: Session, record_id: int) -> Optional[SteelPriceResponse]:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None
        return SteelPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: SteelPriceCreate,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        current_time = now()
        payload = data.model_dump()
        payload["spec"] = self._build_spec(data.thickness, data.width, data.spec)
        payload["final_price_per_ton"] = self._compute_final_price(
            base_price=data.base_price,
            thickness_adjustment=data.thickness_adjustment,
            width_adjustment=data.width_adjustment,
            zinc_adjustment=data.zinc_adjustment,
            processing_fee=data.processing_fee,
            other_adjustment=data.other_adjustment,
        )
        payload["calc_batch_id"] = f"manual-{uuid.uuid4().hex[:16]}"
        payload["match_status"] = "manual"
        payload["calc_status"] = "success"
        payload["calc_message"] = None
        payload["formula_version"] = FORMULA_VERSION
        payload["calculated_at"] = current_time
        payload["audit_status"] = AUDIT_PENDING
        payload["audited_by"] = None
        payload["audited_at"] = None
        payload["audit_remark"] = None
        payload["reverse_audited_by"] = None
        payload["reverse_audited_at"] = None
        payload["reverse_audit_remark"] = None
        payload.update(audit_create(current_user))

        try:
            record = self.repository.create(db, payload)
            db.commit()
            db.refresh(record)
            return SteelPriceResponse.model_validate(record), None
        except IntegrityError as error:
            db.rollback()
            message = (
                f"该业务键已存在：{payload['year']}-{payload['month']:02d}/"
                f"{payload['location']}/{payload['steel_mill']}/"
                f"{payload['category_name']}/{payload['grade']}/"
                f"{payload['thickness']}*{payload['width']}"
            )
            logger.warning("创建钢材价格冲突: %s, error=%s", message, error)
            return None, message
        except Exception as error:
            db.rollback()
            logger.exception("创建钢材价格失败: %s", error)
            return None, str(error)

    def update(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceUpdate,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None, "记录不存在"

        lock_error = self._ensure_not_approved(record)
        if lock_error:
            return None, lock_error

        payload = data.model_dump(exclude_none=True)
        if not payload:
            return None, "未提供任何可更新字段"
        payload.update(audit_update(current_user))

        base_price = payload.get("base_price", record.base_price)
        thickness_adjustment = payload.get("thickness_adjustment", record.thickness_adjustment)
        width_adjustment = payload.get("width_adjustment", record.width_adjustment)
        zinc_adjustment = payload.get("zinc_adjustment", record.zinc_adjustment)
        processing_fee = payload.get("processing_fee", record.processing_fee)
        other_adjustment = payload.get("other_adjustment", record.other_adjustment)
        payload["final_price_per_ton"] = self._compute_final_price(
            base_price=base_price,
            thickness_adjustment=thickness_adjustment,
            width_adjustment=width_adjustment,
            zinc_adjustment=zinc_adjustment,
            processing_fee=processing_fee,
            other_adjustment=other_adjustment,
        )

        try:
            updated = self.repository.update(db, record_id, payload)
            if updated is None:
                db.rollback()
                return None, "记录不存在"
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated), None
        except IntegrityError as error:
            db.rollback()
            logger.warning("更新钢材价格冲突: id=%s, error=%s", record_id, error)
            return None, "更新违反唯一约束"
        except Exception as error:
            db.rollback()
            logger.exception("更新钢材价格失败: id=%s, error=%s", record_id, error)
            return None, str(error)

    def delete(self, db: Session, record_id: int) -> tuple[bool, Optional[str]]:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return False, "记录不存在"

        lock_error = self._ensure_not_approved(record)
        if lock_error:
            return False, lock_error

        try:
            success = self.repository.delete(db, record_id)
            if not success:
                db.rollback()
                return False, "记录不存在"
            db.commit()
            return True, None
        except Exception as error:
            db.rollback()
            logger.exception("删除钢材价格失败: id=%s, error=%s", record_id, error)
            return False, str(error)

    def batch_delete(
        self, db: Session, data: SteelPriceBatchDeleteDTO
    ) -> tuple[Optional[SteelPriceBatchDeleteResultVO], Optional[str]]:
        """
        按筛选条件批量删除未审核记录。

        年度 / 月份 / 基地必填；已审核通过的记录跳过不删。
        """
        location = data.location.strip()
        if not location:
            return None, "基地不能为空"

        category_name = data.category_name.strip() if data.category_name else None
        grade = data.grade.strip() if data.grade else None
        steel_mill = data.steel_mill.strip() if data.steel_mill else None

        try:
            skipped_approved_count = self.repository.count_approved_by_conditions(
                db,
                year=data.year,
                month=data.month,
                location=location,
                category_name=category_name,
                grade=grade,
                steel_mill=steel_mill,
            )
            deleted_count = self.repository.delete_unaudited_by_conditions(
                db,
                year=data.year,
                month=data.month,
                location=location,
                category_name=category_name,
                grade=grade,
                steel_mill=steel_mill,
            )
            db.commit()
            return (
                SteelPriceBatchDeleteResultVO(
                    deleted_count=deleted_count,
                    skipped_approved_count=skipped_approved_count,
                    year=data.year,
                    month=data.month,
                    location=location,
                ),
                None,
            )
        except Exception as error:
            db.rollback()
            logger.exception(
                "批量删除钢材价格失败: year=%s month=%s location=%s",
                data.year,
                data.month,
                location,
            )
            return None, str(error)

    def batch_approve(
        self,
        db: Session,
        data: SteelPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceBatchAuditResultVO], Optional[str]]:
        """
        按年度+月份+基地批量审核通过。

        仅更新 pending / rejected；已通过记录计入 skipped。
        """
        location = data.location.strip()
        if not location:
            return None, "采购基地不能为空"
        audited_by = display_name(current_user)
        if not audited_by:
            return None, "无法识别当前登录用户"
        audit_remark = data.audit_remark.strip() if data.audit_remark else None

        try:
            skipped_count = self.repository.count_by_conditions_and_statuses(
                db,
                year=data.year,
                month=data.month,
                location=location,
                statuses=[AUDIT_APPROVED],
            )
            updated_count = self.repository.approve_by_period(
                db,
                year=data.year,
                month=data.month,
                location=location,
                audited_by=audited_by,
                audited_at=now(),
                audit_remark=audit_remark,
                updated_by=audited_by,
            )
            db.commit()
            return (
                SteelPriceBatchAuditResultVO(
                    updated_count=updated_count,
                    skipped_count=skipped_count,
                    year=data.year,
                    month=data.month,
                    location=location,
                ),
                None,
            )
        except Exception as error:
            db.rollback()
            logger.exception(
                "批量审核失败: year=%s month=%s location=%s",
                data.year,
                data.month,
                location,
            )
            return None, str(error)

    def batch_reverse_audit(
        self,
        db: Session,
        data: SteelPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceBatchAuditResultVO], Optional[str]]:
        """
        按年度+月份+基地批量反审核。

        仅更新 approved → pending；非已通过计入 skipped。
        """
        location = data.location.strip()
        if not location:
            return None, "采购基地不能为空"
        reverse_audited_by = display_name(current_user)
        if not reverse_audited_by:
            return None, "无法识别当前登录用户"
        reverse_audit_remark = data.reverse_audit_remark.strip()
        if not reverse_audit_remark:
            return None, "反审核原因必填"

        try:
            skipped_count = self.repository.count_by_conditions_and_statuses(
                db,
                year=data.year,
                month=data.month,
                location=location,
                statuses=[AUDIT_PENDING, AUDIT_REJECTED],
            )
            updated_count = self.repository.reverse_audit_by_period(
                db,
                year=data.year,
                month=data.month,
                location=location,
                reverse_audited_by=reverse_audited_by,
                reverse_audited_at=now(),
                reverse_audit_remark=reverse_audit_remark,
                updated_by=reverse_audited_by,
            )
            db.commit()
            return (
                SteelPriceBatchAuditResultVO(
                    updated_count=updated_count,
                    skipped_count=skipped_count,
                    year=data.year,
                    month=data.month,
                    location=location,
                ),
                None,
            )
        except Exception as error:
            db.rollback()
            logger.exception(
                "批量反审核失败: year=%s month=%s location=%s",
                data.year,
                data.month,
                location,
            )
            return None, str(error)

    def approve(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceAuditDTO,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None, "记录不存在"
        if record.audit_status == AUDIT_APPROVED:
            return None, "记录已是审核通过状态"
        if record.audit_status not in (AUDIT_PENDING, AUDIT_REJECTED):
            return None, f"当前状态不允许审核通过: {record.audit_status}"

        try:
            operator_name = display_name(current_user)
            updated = self.repository.update(
                db,
                record_id,
                {
                    "audit_status": AUDIT_APPROVED,
                    "audited_by": operator_name,
                    "audited_at": now(),
                    "audit_remark": data.audit_remark,
                    **audit_update(current_user),
                },
            )
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated), None
        except Exception as error:
            db.rollback()
            logger.exception("审核通过失败: id=%s, error=%s", record_id, error)
            return None, str(error)

    def reject(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceAuditDTO,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None, "记录不存在"
        if record.audit_status == AUDIT_APPROVED:
            return None, "已通过记录请先反审核，再驳回"
        if record.audit_status != AUDIT_PENDING:
            return None, f"当前状态不允许驳回: {record.audit_status}"

        try:
            operator_name = display_name(current_user)
            updated = self.repository.update(
                db,
                record_id,
                {
                    "audit_status": AUDIT_REJECTED,
                    "audited_by": operator_name,
                    "audited_at": now(),
                    "audit_remark": data.audit_remark,
                    **audit_update(current_user),
                },
            )
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated), None
        except Exception as error:
            db.rollback()
            logger.exception("审核驳回失败: id=%s, error=%s", record_id, error)
            return None, str(error)

    def reverse_audit(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceReverseAuditDTO,
        current_user: UserVO,
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None, "记录不存在"
        if record.audit_status != AUDIT_APPROVED:
            return None, "仅已通过记录可以反审核"

        try:
            updated = self.repository.update(
                db,
                record_id,
                {
                    "audit_status": AUDIT_PENDING,
                    "reverse_audited_by": display_name(current_user),
                    "reverse_audited_at": now(),
                    "reverse_audit_remark": data.reverse_audit_remark.strip(),
                    **audit_update(current_user),
                },
            )
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated), None
        except Exception as error:
            db.rollback()
            logger.exception("反审核失败: id=%s, error=%s", record_id, error)
            return None, str(error)

    def save_calc_batch(
        self,
        db: Session,
        *,
        calc_batch_id: str,
        rows: list[dict],
        current_user: UserVO,
    ) -> dict[str, int]:
        """
        批量落库计算结果。

        - 业务键已存在且 audit_status=approved → 跳过（不覆盖）
        - 业务键已存在且非 approved → 更新计算结果字段，重置为 pending
        - 业务键不存在 → 新建，audit_status=pending
        """
        create_audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        created_count = 0
        updated_count = 0
        skipped_approved_count = 0
        failed_count = 0
        current_time = now()

        try:
            for payload in rows:
                try:
                    existing = self.repository.get_by_business_key(
                        db,
                        year=payload["year"],
                        month=payload["month"],
                        location=payload["location"],
                        steel_mill=payload["steel_mill"],
                        category_name=payload["category_name"],
                        grade=payload["grade"],
                        thickness=payload["thickness"],
                        width=payload["width"],
                    )
                    if existing is not None and existing.audit_status == AUDIT_APPROVED:
                        skipped_approved_count += 1
                        continue

                    write_payload = {
                        **payload,
                        "calc_batch_id": calc_batch_id,
                        "formula_version": payload.get("formula_version") or FORMULA_VERSION,
                        "calculated_at": current_time,
                        "audit_status": AUDIT_PENDING,
                        "audited_by": None,
                        "audited_at": None,
                        "audit_remark": None,
                        "reverse_audited_by": None,
                        "reverse_audited_at": None,
                        "reverse_audit_remark": None,
                    }

                    if existing is None:
                        write_payload.update(create_audit)
                        self.repository.create(db, write_payload)
                        created_count += 1
                    else:
                        write_payload.update(update_audit)
                        self.repository.update(db, existing.id, write_payload)
                        updated_count += 1
                except Exception as row_error:
                    failed_count += 1
                    logger.exception(
                        "计算落库单行失败: batch=%s grade=%s error=%s",
                        calc_batch_id,
                        payload.get("grade"),
                        row_error,
                    )

            db.commit()
        except Exception as error:
            db.rollback()
            logger.exception("计算批次落库失败: batch=%s error=%s", calc_batch_id, error)
            raise

        logger.info(
            "计算批次落库完成: batch=%s created=%s updated=%s skipped_approved=%s failed=%s",
            calc_batch_id,
            created_count,
            updated_count,
            skipped_approved_count,
            failed_count,
        )
        return {
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_approved_count": skipped_approved_count,
            "failed_count": failed_count,
        }
