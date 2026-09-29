"""钢材价格：计算批次落库（已审不覆盖）。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, display_name
from app.common.timezone import now
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import SteelPriceWrite
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.pricing import FORMULA_VERSION

logger = logging.getLogger("service.steel_price")


def save_calc_batch(
    repository: SteelPriceRepository,
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
                existing = repository.get_by_business_key(
                    db,
                    year=write.year,
                    month=write.month,
                    location=write.location,
                    steel_mill_id=write.steel_mill_id,
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
                    repository.create(db, write)
                    created_count += 1
                else:
                    write.updated_by = operator_name
                    repository.update(db, existing.id, write)
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
