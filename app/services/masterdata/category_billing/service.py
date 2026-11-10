"""计费管理：一个分类选用哪些费用。费率读费用档案，不另存。"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create
from app.common.money import Q6, quantize_money
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
from app.services.masterdata.assembly_category.seed import ASSEMBLY_CATEGORY_SEEDS
from app.services.masterdata.category_billing.rates import FinishedFeeRates
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

    def check_missing_seed_fees(self, db: Session, fee_codes: tuple[str, ...]) -> None:
        """刚补进档案的种子费用，给四个种子分类勾上。不改用户已经改过的勾选。"""
        if not fee_codes:
            return
        audit = audit_create(SYSTEM_USER)
        written = 0
        for category_seed in ASSEMBLY_CATEGORY_SEEDS:
            category = self.categories.get_by_code(db, category_seed.code)
            if category is None:
                continue
            for fee_code in fee_codes:
                fee = self.fees.get_by_code(db, fee_code)
                if fee is None or self.repository.pair_exists(db, category.id, fee.id):
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
            return
        db.commit()
        logger.info("已为新费用补勾选 %s 行", written)

    def finished_fee_rates(
        self,
        db: Session,
        *,
        category_code: str | None = None,
    ) -> FinishedFeeRates:
        """启用分类里勾上、且费用仍启用的计费率。没勾上的项是 0。

        现库报废费用的稳定键是 scrap，也认已经建过的 scrap_expense。
        """
        by_code: dict[str, Decimal] = {}
        for code, rate in self.repository.list_enabled_checked_rates(
            db, category_code=category_code
        ):
            amount = quantize_money(rate, Q6)
            by_code[code] = amount
            if code == "scrap_expense":
                by_code["scrap"] = amount
        zero = Decimal("0")
        return FinishedFeeRates(
            finance_rate=by_code.get("financial", zero),
            management_rate=by_code.get("management", zero),
            warehouse_packaging_rate=by_code.get("warehouse_packaging", zero),
            scrap_rate=by_code.get("scrap", zero),
            pretax_profit_rate=by_code.get("pretax_profit", zero),
        )

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
