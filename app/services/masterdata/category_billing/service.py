"""计费管理：一个分类选用哪些费用。费率读费用档案，不另存。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.category_billing import AssemblyCategoryBilling
from app.models.masterdata.fee_archive import FeeArchive
from app.repositories.masterdata.assembly_category import AssemblyCategoryRepository
from app.repositories.masterdata.category_billing import AssemblyCategoryBillingRepository
from app.repositories.masterdata.fee_archive import FeeArchiveRepository
from app.schemas.dto.category_billing_dto import (
    AssemblyCategoryBillingInsert,
    AssemblyCategoryBillingQuery,
    CategoryBillingReplace,
)
from app.schemas.vo.category_billing_vo import (
    AssemblyCategoryBillingVO,
    CategoryBillingSelectionVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.category_billing.seed import BILLING_SEED_PAIRS

logger = logging.getLogger("service.category_billing")


class AssemblyCategoryBillingService:
    """计费对照。组合总成分类和费用档案，不改那两张表。"""

    def __init__(self) -> None:
        self.repository = AssemblyCategoryBillingRepository()
        self.categories = AssemblyCategoryRepository()
        self.fees = FeeArchiveRepository()

    def drop_retired_columns(self, db: Session) -> None:
        """去掉对照行上已不用的顺序和启用。已是新结构则不动。"""
        if not self.repository.drop_retired_columns(db):
            return
        db.commit()
        logger.info("计费对照已去掉顺序和启用列")

    def ensure_seed_if_empty(self, db: Session) -> None:
        """计费表为空时，按现网五项给每个分类勾上。已有行不覆盖。"""
        if self.repository.count(db) > 0:
            return
        audit = audit_create(SYSTEM_USER)
        written = 0
        for category_code, fee_code in BILLING_SEED_PAIRS:
            category = self.categories.get_by_code(db, category_code)
            fee = self.fees.get_by_code(db, fee_code)
            if category is None or fee is None:
                logger.warning("计费种子跳过，分类或费用不在库：%s / %s", category_code, fee_code)
                continue
            self.repository.create(
                db,
                AssemblyCategoryBillingInsert(
                    assembly_category_id=category.id,
                    fee_archive_id=fee.id,
                    remark=None,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            written += 1
        if written == 0:
            db.rollback()
            return
        db.commit()
        logger.info("已写入计费种子 %s 行", written)

    def list_page(
        self,
        db: Session,
        query: AssemblyCategoryBillingQuery,
    ) -> tuple[list[AssemblyCategoryBillingVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            assembly_category_id=query.assembly_category_id,
            skip=skip,
            limit=query.size,
        )
        return [self._vo(row) for row in rows], total

    def replace_selection(
        self,
        db: Session,
        category_id: int,
        dto: CategoryBillingReplace,
        current_user: UserVO,
    ) -> CategoryBillingSelectionVO:
        """用勾选结果替换这个分类的费用。未勾选的对照删除，已有行保留备注。"""
        category = self.categories.get_by_id(db, category_id)
        if category is None:
            raise NotFoundException("总成分类不存在")
        if not category.is_enabled:
            raise BusinessException("分类已停用，不能再选用")
        existing = self.repository.list_for_category(db, category.id)
        existing_by_fee = {row.fee_archive_id: row for row in existing}
        chosen = [
            self._require_fee(
                db, fee_id, keep_disabled_id=fee_id if fee_id in existing_by_fee else None
            )
            for fee_id in dto.fee_archive_ids
        ]
        chosen.sort(key=lambda fee: (fee.sort_order, fee.code, fee.id))
        wanted = {fee.id for fee in chosen}
        audit = audit_create(current_user)
        try:
            for row in existing:
                if row.fee_archive_id not in wanted:
                    self.repository.delete(db, row)
            for fee in chosen:
                if fee.id in existing_by_fee:
                    continue
                self.repository.create(
                    db,
                    AssemblyCategoryBillingInsert(
                        assembly_category_id=category.id,
                        fee_archive_id=fee.id,
                        remark=None,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    ),
                )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise BusinessException("该分类已选用此费用", code=409) from exc
        db.expire_all()
        rows = self.repository.list_for_category(db, category.id)
        return CategoryBillingSelectionVO(
            assembly_category_id=category.id,
            assembly_category_name=category.name,
            assembly_category_enabled=category.is_enabled,
            items=[self._vo(row) for row in rows],
        )

    def _require_fee(
        self,
        db: Session,
        fee_id: int,
        *,
        keep_disabled_id: int | None,
    ) -> FeeArchive:
        row = self.fees.get_by_id(db, fee_id)
        if row is None:
            raise NotFoundException("费用档案不存在")
        if not row.is_enabled and row.id != keep_disabled_id:
            raise BusinessException("费用已停用，不能再选用")
        return row

    def _vo(self, row: AssemblyCategoryBilling) -> AssemblyCategoryBillingVO:
        return AssemblyCategoryBillingVO(
            id=row.id,
            assembly_category_id=row.assembly_category_id,
            assembly_category_code=row.category.code,
            assembly_category_name=row.category.name,
            assembly_category_enabled=row.category.is_enabled,
            fee_archive_id=row.fee_archive_id,
            fee_code=row.fee.code,
            fee_name=row.fee.name,
            fee_enabled=row.fee.is_enabled,
            charge_basis=row.fee.charge_basis,
            charge_rate=row.fee.charge_rate,
            remark=row.remark,
            created_by=row.created_by,
            updated_by=row.updated_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
