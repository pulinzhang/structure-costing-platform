"""钢材价格业务服务（门面，符号路径保持不变）。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.costing import SteelPrice
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import (
    SteelPriceAuditDTO,
    SteelPriceBatchApproveDTO,
    SteelPriceBatchDeleteDTO,
    SteelPriceBatchReverseAuditDTO,
    SteelPriceCreate,
    SteelPriceQuery,
    SteelPriceReverseAuditDTO,
    SteelPriceUpdate,
    SteelPriceWrite,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceBatchAuditResultVO,
    SteelPriceBatchDeleteResultVO,
    SteelPriceFilterOptionsVO,
    SteelPriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.audit import (
    approve_steel_price,
    batch_approve_steel_prices,
    batch_reverse_audit_steel_prices,
    reject_steel_price,
    reverse_audit_steel_price,
)
from app.services.costing.steel_price.calc_batch import save_calc_batch
from app.services.costing.steel_price.crud import (
    batch_delete_steel_prices,
    create_steel_price,
    delete_steel_price,
    get_steel_price,
    update_steel_price,
)
from app.services.costing.steel_price.paginate import paginate_steel_prices
from app.services.costing.steel_price.pricing import (
    FORMULA_VERSION,
    build_spec_or_none,
    compute_final_price,
    ensure_not_approved,
)

__all__ = ["FORMULA_VERSION", "SteelPriceService"]


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
        return compute_final_price(
            base_price=base_price,
            thickness_adjustment=thickness_adjustment,
            width_adjustment=width_adjustment,
            zinc_adjustment=zinc_adjustment,
            processing_fee=processing_fee,
            other_adjustment=other_adjustment,
        )

    @staticmethod
    def _build_spec(thickness: Decimal, width: Decimal, spec: str | None) -> str | None:
        return build_spec_or_none(thickness, width, spec)

    def _ensure_not_approved(self, record: SteelPrice) -> None:
        ensure_not_approved(record)

    def paginate(
        self, db: Session, query: SteelPriceQuery
    ) -> tuple[list[SteelPriceResponse], int, SteelPriceFilterOptionsVO]:
        return paginate_steel_prices(self.repository, db, query)

    def get_by_id(self, db: Session, record_id: int) -> SteelPriceResponse:
        return get_steel_price(self.repository, db, record_id)

    def create(
        self,
        db: Session,
        data: SteelPriceCreate,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        return create_steel_price(self.repository, db, data, current_user)

    def update(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceUpdate,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        return update_steel_price(self.repository, db, record_id, data, current_user)

    def delete(self, db: Session, record_id: int) -> None:
        delete_steel_price(self.repository, db, record_id)

    def batch_delete(
        self, db: Session, data: SteelPriceBatchDeleteDTO
    ) -> SteelPriceBatchDeleteResultVO:
        return batch_delete_steel_prices(self.repository, db, data)

    def batch_approve(
        self,
        db: Session,
        data: SteelPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> SteelPriceBatchAuditResultVO:
        return batch_approve_steel_prices(self.repository, db, data, current_user)

    def batch_reverse_audit(
        self,
        db: Session,
        data: SteelPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceBatchAuditResultVO:
        return batch_reverse_audit_steel_prices(self.repository, db, data, current_user)

    def approve(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        return approve_steel_price(self.repository, db, record_id, data, current_user)

    def reject(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        return reject_steel_price(self.repository, db, record_id, data, current_user)

    def reverse_audit(
        self,
        db: Session,
        record_id: int,
        data: SteelPriceReverseAuditDTO,
        current_user: UserVO,
    ) -> SteelPriceResponse:
        return reverse_audit_steel_price(self.repository, db, record_id, data, current_user)

    def save_calc_batch(
        self,
        db: Session,
        *,
        calc_batch_id: str,
        rows: list[SteelPriceWrite],
        current_user: UserVO,
    ) -> dict[str, int]:
        return save_calc_batch(
            self.repository,
            db,
            calc_batch_id=calc_batch_id,
            rows=rows,
            current_user=current_user,
        )
