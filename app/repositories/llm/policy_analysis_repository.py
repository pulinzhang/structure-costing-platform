"""加减价政策 — LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.masterdata.steel_mill import SteelMill
from app.models.yishiyiyi.steel_price_policy import SteelPriceLadderItem, SteelPricePolicy
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class PolicyLadderRow:
    policy_id: int
    year: int
    month: int
    steel_mill: str
    steel_mill_id: int
    category_name: str
    policy_type: str
    grade_value: str | None
    base_thickness: Decimal | None
    price_adjustment: int
    thick_min: Decimal | None
    thick_max: Decimal | None
    is_base: int


class PolicyAnalysisRepository:
    def query_ladder_rows(
        self,
        db: Session,
        *,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        steel_mill_id: int | None = None,
        category_name: str | None = None,
        policy_type: str | None = None,
        limit: int = 8000,
    ) -> list[PolicyLadderRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = SteelPricePolicy.year * 100 + SteelPricePolicy.month

        q = (
            db.query(SteelPricePolicy, SteelPriceLadderItem, SteelMill.abbreviation)
            .join(SteelPriceLadderItem, SteelPriceLadderItem.policy_id == SteelPricePolicy.id)
            .outerjoin(SteelMill, SteelMill.id == SteelPricePolicy.steel_mill_id)
            .filter(ym_expr >= start, ym_expr <= end)
        )
        if steel_mill_id is not None:
            q = q.filter(SteelPricePolicy.steel_mill_id == steel_mill_id)
        if category_name:
            q = q.filter(SteelPricePolicy.category_name == category_name)
        if policy_type:
            q = q.filter(SteelPricePolicy.policy_type == policy_type)

        q = q.order_by(
            SteelPricePolicy.year.asc(),
            SteelPricePolicy.month.asc(),
            SteelPricePolicy.steel_mill.asc(),
            SteelPriceLadderItem.sort_order.asc(),
        ).limit(limit)

        rows: list[PolicyLadderRow] = []
        for policy, item, abbreviation in q.all():
            rows.append(
                PolicyLadderRow(
                    policy_id=int(policy.id),
                    year=int(policy.year),
                    month=int(policy.month),
                    steel_mill=str(abbreviation or policy.steel_mill),
                    steel_mill_id=int(policy.steel_mill_id),
                    category_name=str(policy.category_name),
                    policy_type=str(policy.policy_type),
                    grade_value=policy.grade_value,
                    base_thickness=(
                        Decimal(str(policy.base_thickness))
                        if policy.base_thickness is not None
                        else None
                    ),
                    price_adjustment=int(item.price_adjustment),
                    thick_min=(
                        Decimal(str(item.thick_min)) if item.thick_min is not None else None
                    ),
                    thick_max=(
                        Decimal(str(item.thick_max)) if item.thick_max is not None else None
                    ),
                    is_base=int(item.is_base or 0),
                )
            )
        return rows

    def query_policies(
        self,
        db: Session,
        *,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        steel_mill: str | None = None,
        category_name: str | None = None,
        policy_type: str | None = None,
        limit: int = 2000,
    ) -> list[SteelPricePolicy]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = SteelPricePolicy.year * 100 + SteelPricePolicy.month

        q = db.query(SteelPricePolicy).options(joinedload(SteelPricePolicy.items))
        q = q.filter(ym_expr >= start, ym_expr <= end)
        if steel_mill:
            q = q.filter(SteelPricePolicy.steel_mill == steel_mill)
        if category_name:
            q = q.filter(SteelPricePolicy.category_name == category_name)
        if policy_type:
            q = q.filter(SteelPricePolicy.policy_type == policy_type)
        return (
            q.order_by(
                SteelPricePolicy.year.asc(),
                SteelPricePolicy.month.asc(),
                SteelPricePolicy.steel_mill.asc(),
            )
            .limit(limit)
            .all()
        )
