"""钢材价格业务服务。"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    AUDIT_REJECTED,
    audit_create,
    display_name,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.costing import SteelPrice
from app.repositories.costing.steel_price import SteelPriceRepository
from app.schemas.dto.steel_price_dto import (
    SteelPriceAuditDTO,
    SteelPriceBatchApproveDTO,
    SteelPriceBatchDeleteDTO,
    SteelPriceBatchReverseAuditDTO,
    SteelPriceCreate,
    SteelPricePatch,
    SteelPriceQuery,
    SteelPriceReverseAuditDTO,
    SteelPriceUpdate,
    SteelPriceWrite,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceBatchAuditResultVO,
    SteelPriceBatchDeleteResultVO,
    SteelPriceFilterOptionsVO,
    SteelPriceListSummaryVO,
    SteelPriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.spec_format import build_spec
from app.services.masterdata.location.location_service import LocationService

logger = logging.getLogger("service.steel_price")

FORMULA_VERSION = "v1"


class SteelPriceService:
    """钢材价格查询、手工维护与审核业务。"""

    def __init__(self) -> None:
        self.repository = SteelPriceRepository()

    @staticmethod
    def _compute_final_price(
        *,
        base_price: Decimal,
        thickness_adjustment: Decimal,
        width_adjustment: Decimal,
        zinc_adjustment: Decimal,
        processing_fee: Decimal,
        other_adjustment: Decimal,
    ) -> Decimal:
        return (
            base_price
            + thickness_adjustment
            + width_adjustment
            + zinc_adjustment
            + processing_fee
            + other_adjustment
        )

    @staticmethod
    def _build_spec(thickness: Decimal, width: Decimal, spec: str | None) -> str | None:
        if spec and spec.strip():
            return spec.strip()
        return build_spec(thickness, width) or None

    def _ensure_not_approved(self, record: SteelPrice) -> None:
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("记录已审核通过，请先反审核后再修改/删除/重算")

    def paginate(
        self, db: Session, query: SteelPriceQuery
    ) -> tuple[list[SteelPriceResponse], int, SteelPriceFilterOptionsVO]:
        skip = (query.page - 1) * query.size
        year = query.year
        month = query.month
        location_raw = query.location.strip() if query.location else None
        category_name = query.category_name.strip() if query.category_name else None
        grade = query.grade.strip() if query.grade else None
        steel_mill = query.steel_mill.strip() if query.steel_mill else None
        audit_status = query.audit_status.strip() if query.audit_status else None
        location_service = LocationService()
        locations: list[str] | None = None
        if location_raw:
            locations = location_service.expand_for_query(db, location_raw)
            if not locations:
                options = self.repository.get_filter_options(db)
                return (
                    [],
                    0,
                    SteelPriceFilterOptionsVO(
                        years=list(options["years"]),
                        months=list(options["months"]),
                        locations=location_service.list_registered(db),
                        category_names=list(options["category_names"]),
                        steel_mills=list(options["steel_mills"]),
                        audit_statuses=list(options["audit_statuses"]),
                        summary=SteelPriceListSummaryVO(),
                    ),
                )
        records, total = self.repository.paginate(
            db,
            year=year,
            month=month,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
            skip=skip,
            limit=query.size,
        )
        rows = [SteelPriceResponse.model_validate(record) for record in records]
        options = self.repository.get_filter_options(db)
        filters = SteelPriceFilterOptionsVO(
            years=list(options["years"]),
            months=list(options["months"]),
            locations=location_service.list_registered(db),
            category_names=list(options["category_names"]),
            steel_mills=list(options["steel_mills"]),
            audit_statuses=list(options["audit_statuses"]),
            summary=SteelPriceListSummaryVO.model_validate(
                self.repository.summarize_by_filters(
                    db,
                    year=year,
                    month=month,
                    locations=locations,
                    category_name=category_name,
                    grade=grade,
                    steel_mill=steel_mill,
                    audit_status=audit_status,
                )
            ),
        )
        return rows, total, filters

    def get_by_id(self, db: Session, record_id: int) -> SteelPriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")
        return SteelPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: SteelPriceCreate,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        current_time = now()
        audit = audit_create(current_user)
        write = SteelPriceWrite(
            year=data.year,
            month=data.month,
            location=data.location,
            steel_mill=data.steel_mill,
            category_name=data.category_name,
            grade=data.grade,
            thickness=data.thickness,
            width=data.width,
            spec=self._build_spec(data.thickness, data.width, data.spec),
            base_price=data.base_price,
            thickness_adjustment=data.thickness_adjustment,
            width_adjustment=data.width_adjustment,
            zinc_adjustment=data.zinc_adjustment,
            processing_fee=data.processing_fee,
            other_adjustment=data.other_adjustment,
            final_price_per_ton=self._compute_final_price(
                base_price=data.base_price,
                thickness_adjustment=data.thickness_adjustment,
                width_adjustment=data.width_adjustment,
                zinc_adjustment=data.zinc_adjustment,
                processing_fee=data.processing_fee,
                other_adjustment=data.other_adjustment,
            ),
            calc_batch_id=f"manual-{uuid.uuid4().hex[:16]}",
            match_status="manual",
            calc_status="success",
            calc_message=None,
            formula_version=FORMULA_VERSION,
            calculated_at=current_time,
            audit_status=AUDIT_PENDING,
            remark=data.remark,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )

        try:
            record = self.repository.create(db, write)
            db.commit()
            db.refresh(record)
            return SteelPriceResponse.model_validate(record)
        except IntegrityError as error:
            db.rollback()
            message = (
                f"该业务键已存在：{write.year}-{write.month:02d}/"
                f"{write.location}/{write.steel_mill}/"
                f"{write.category_name}/{write.grade}/"
                f"{write.thickness}*{write.width}"
            )
            logger.warning("创建钢材价格冲突: %s, error=%s", message, error)
            raise BusinessException(message) from error
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建钢材价格失败")
            raise

    def update(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceUpdate,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")

        self._ensure_not_approved(record)

        payload: SteelPricePatch = {}
        if data.base_price is not None:
            payload["base_price"] = data.base_price
        if data.thickness_adjustment is not None:
            payload["thickness_adjustment"] = data.thickness_adjustment
        if data.width_adjustment is not None:
            payload["width_adjustment"] = data.width_adjustment
        if data.zinc_adjustment is not None:
            payload["zinc_adjustment"] = data.zinc_adjustment
        if data.processing_fee is not None:
            payload["processing_fee"] = data.processing_fee
        if data.other_adjustment is not None:
            payload["other_adjustment"] = data.other_adjustment
        if data.spec is not None:
            payload["spec"] = data.spec
        if data.remark is not None:
            payload["remark"] = data.remark
        if not payload:
            raise BusinessException("未提供任何可更新字段")

        payload["updated_by"] = display_name(current_user)
        payload["final_price_per_ton"] = self._compute_final_price(
            base_price=payload.get("base_price", record.base_price),
            thickness_adjustment=payload.get("thickness_adjustment", record.thickness_adjustment),
            width_adjustment=payload.get("width_adjustment", record.width_adjustment),
            zinc_adjustment=payload.get("zinc_adjustment", record.zinc_adjustment),
            processing_fee=payload.get("processing_fee", record.processing_fee),
            other_adjustment=payload.get("other_adjustment", record.other_adjustment),
        )

        try:
            updated = self.repository.update(db, record_id, payload)
            if updated is None:
                db.rollback()
                raise NotFoundException("记录不存在")
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated)
        except IntegrityError as error:
            db.rollback()
            logger.warning("更新钢材价格冲突: id=%s, error=%s", record_id, error)
            raise BusinessException("更新违反唯一约束") from error
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新钢材价格失败: id=%s", record_id)
            raise

    def delete(self, db: Session, record_id: int) -> None:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")

        self._ensure_not_approved(record)

        try:
            success = self.repository.delete(db, record_id)
            if not success:
                db.rollback()
                raise NotFoundException("记录不存在")
            db.commit()
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除钢材价格失败: id=%s", record_id)
            raise

    def batch_delete(
        self, db: Session, data: SteelPriceBatchDeleteDTO
    ) -> SteelPriceBatchDeleteResultVO:
        """
        按筛选条件批量删除未审核记录。

        年度 / 月份 / 基地必填；已审核通过的记录跳过不删。
        """
        location = data.location.strip()
        if not location:
            raise BusinessException("基地不能为空")

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
            return SteelPriceBatchDeleteResultVO(
                deleted_count=deleted_count,
                skipped_approved_count=skipped_approved_count,
                year=data.year,
                month=data.month,
                location=location,
            )
        except Exception:
            db.rollback()
            logger.exception(
                "批量删除钢材价格失败: year=%s month=%s location=%s",
                data.year,
                data.month,
                location,
            )
            raise

    def batch_approve(
        self,
        db: Session,
        data: SteelPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> SteelPriceBatchAuditResultVO:
        """
        按年度+月份+基地批量审核通过。

        仅更新 pending / rejected；已通过记录计入 skipped。
        """
        location = data.location.strip()
        if not location:
            raise BusinessException("采购基地不能为空")
        audited_by = display_name(current_user)
        if not audited_by:
            raise BusinessException("无法识别当前登录用户")
        audit_remark = data.audit_remark.strip()
        if not audit_remark:
            raise BusinessException("审核意见必填")

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
            return SteelPriceBatchAuditResultVO(
                updated_count=updated_count,
                skipped_count=skipped_count,
                year=data.year,
                month=data.month,
                location=location,
            )
        except Exception:
            db.rollback()
            logger.exception(
                "批量审核失败: year=%s month=%s location=%s",
                data.year,
                data.month,
                location,
            )
            raise

    def batch_reverse_audit(
        self,
        db: Session,
        data: SteelPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceBatchAuditResultVO:
        """
        按年度+月份+基地批量反审核。

        仅更新 approved → pending；非已通过计入 skipped。
        """
        location = data.location.strip()
        if not location:
            raise BusinessException("采购基地不能为空")
        reverse_audited_by = display_name(current_user)
        if not reverse_audited_by:
            raise BusinessException("无法识别当前登录用户")
        reverse_audit_remark = data.reverse_audit_remark.strip()
        if not reverse_audit_remark:
            raise BusinessException("反审核原因必填")

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
            return SteelPriceBatchAuditResultVO(
                updated_count=updated_count,
                skipped_count=skipped_count,
                year=data.year,
                month=data.month,
                location=location,
            )
        except Exception:
            db.rollback()
            logger.exception(
                "批量反审核失败: year=%s month=%s location=%s",
                data.year,
                data.month,
                location,
            )
            raise

    def approve(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("记录已是审核通过状态")
        if record.audit_status not in (AUDIT_PENDING, AUDIT_REJECTED):
            raise BusinessException(f"当前状态不允许审核通过: {record.audit_status}")

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
                    "updated_by": operator_name,
                },
            )
            if updated is None:
                raise NotFoundException("记录不存在")
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("审核通过失败: id=%s", record_id)
            raise

    def reject(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已通过记录请先反审核，再驳回")
        if record.audit_status != AUDIT_PENDING:
            raise BusinessException(f"当前状态不允许驳回: {record.audit_status}")

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
                    "updated_by": operator_name,
                },
            )
            if updated is None:
                raise NotFoundException("记录不存在")
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("审核驳回失败: id=%s", record_id)
            raise

    def reverse_audit(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceReverseAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            raise NotFoundException("记录不存在")
        if record.audit_status != AUDIT_APPROVED:
            raise BusinessException("仅已通过记录可以反审核")

        try:
            operator_name = display_name(current_user)
            updated = self.repository.update(
                db,
                record_id,
                {
                    "audit_status": AUDIT_PENDING,
                    "reverse_audited_by": operator_name,
                    "reverse_audited_at": now(),
                    "reverse_audit_remark": data.reverse_audit_remark.strip(),
                    "updated_by": operator_name,
                },
            )
            if updated is None:
                raise NotFoundException("记录不存在")
            db.commit()
            db.refresh(updated)
            return SteelPriceResponse.model_validate(updated)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("反审核失败: id=%s", record_id)
            raise

    def save_calc_batch(
        self,
        db: Session,
        *,
        calc_batch_id: str,
        rows: list[SteelPriceWrite],
        current_user: UserVO,
    ) -> dict[str, int]:
        """
        批量落库计算结果。

        - 业务键已存在且 audit_status=approved → 跳过（不覆盖）
        - 业务键已存在且非 approved → 更新计算结果字段，重置为 pending
        - 业务键不存在 → 新建，audit_status=pending
        """
        create_audit = audit_create(current_user)
        operator_name = display_name(current_user)
        created_count = 0
        updated_count = 0
        skipped_approved_count = 0
        failed_count = 0
        current_time = now()

        try:
            for write in rows:
                try:
                    existing = self.repository.get_by_business_key(
                        db,
                        year=write.year,
                        month=write.month,
                        location=write.location,
                        steel_mill=write.steel_mill,
                        category_name=write.category_name,
                        grade=write.grade,
                        thickness=write.thickness,
                        width=write.width,
                    )
                    if existing is not None and existing.audit_status == AUDIT_APPROVED:
                        skipped_approved_count += 1
                        continue

                    write.calc_batch_id = calc_batch_id
                    write.formula_version = write.formula_version or FORMULA_VERSION
                    write.calculated_at = current_time
                    write.audit_status = AUDIT_PENDING
                    write.audited_by = None
                    write.audited_at = None
                    write.audit_remark = None
                    write.reverse_audited_by = None
                    write.reverse_audited_at = None
                    write.reverse_audit_remark = None

                    if existing is None:
                        write.created_by = create_audit["created_by"]
                        write.updated_by = create_audit["updated_by"]
                        self.repository.create(db, write)
                        created_count += 1
                    else:
                        write.updated_by = operator_name
                        self.repository.update(db, existing.id, write)
                        updated_count += 1
                except Exception as row_error:
                    failed_count += 1
                    logger.exception(
                        "计算落库单行失败: batch=%s grade=%s error=%s",
                        calc_batch_id,
                        write.grade,
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
