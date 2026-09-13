"""树根核价卡材料行：构成、材料单价、标准件价。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.repositories.llm._query_guard import run_guarded_query
from app.repositories.llm.cost_analysis.rows import L0CompositionLineRow
from app.repositories.llm.cost_analysis.scope import apply_assembly_cost_scope
from app.services.llm._money import ym_int


def _line_from_card_item(card: AssemblyCost, item: AssemblyCostItem) -> L0CompositionLineRow:
    return L0CompositionLineRow(
        year=int(card.year),
        month=int(card.month),
        root_part_number=str(card.part_number),
        root_part_name=card.part_name,
        root_should_cost=Decimal(str(card.should_cost or card.total_amount or 0)),
        child_part_number=str(item.part_number),
        child_part_name=item.part_name,
        cost_source=str(item.cost_source or ""),
        unit_price=Decimal(str(item.unit_price or 0)),
        effective_qty=Decimal(str(item.effective_qty or 0)),
        line_amount=Decimal(str(item.line_amount or 0)),
        supply_type=item.supply_type,
        location=str(card.location) if card.location else None,
    )


class L0CompositionRepository:
    def query_item_price_rows(
        self,
        db: Session,
        *,
        part_number: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        limit: int = 200,
        trace_id: str | None = None,
    ) -> list[L0CompositionLineRow]:
        """按材料行零件号取核价表单价（标准件/外购件挂在总成卡下）。"""
        return run_guarded_query(
            sql_summary="costing_assembly_cost_items.query_item_price_rows",
            trace_id=trace_id,
            query_fn=lambda: self._query_item_price_rows_impl(
                db,
                part_number=part_number,
                start_year=start_year,
                start_month=start_month,
                end_year=end_year,
                end_month=end_month,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                limit=limit,
            ),
        )

    def query_composition_lines(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        part_number: str | None = None,
        limit: int = 4000,
        trace_id: str | None = None,
    ) -> list[L0CompositionLineRow]:
        return run_guarded_query(
            sql_summary="costing_assembly_cost_items.query_composition_lines",
            trace_id=trace_id,
            query_fn=lambda: self._query_composition_lines_impl(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                start_year=start_year,
                start_month=start_month,
                end_year=end_year,
                end_month=end_month,
                part_number=part_number,
                limit=limit,
            ),
        )

    def query_standard_part_price_lines(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        min_unit_price: Decimal,
        supply_types: tuple[str, ...],
        name_keys: tuple[str, ...],
        part_number: str | None = None,
        limit: int = 500,
        trace_id: str | None = None,
    ) -> list[L0CompositionLineRow]:
        return run_guarded_query(
            sql_summary="costing_assembly_cost_items.query_standard_part_price_lines",
            trace_id=trace_id,
            query_fn=lambda: self._query_standard_part_price_lines_impl(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                start_year=start_year,
                start_month=start_month,
                end_year=end_year,
                end_month=end_month,
                min_unit_price=min_unit_price,
                supply_types=supply_types,
                name_keys=name_keys,
                part_number=part_number,
                limit=limit,
            ),
        )

    def _query_item_price_rows_impl(
        self,
        db: Session,
        *,
        part_number: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        limit: int,
    ) -> list[L0CompositionLineRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = AssemblyCost.year * 100 + AssemblyCost.month
        pattern = f"%{escape_like_fragment(part_number)}%"
        q = (
            db.query(AssemblyCost, AssemblyCostItem)
            .join(
                AssemblyCostItem,
                AssemblyCostItem.assembly_cost_id == AssemblyCost.id,
            )
            .filter(
                ym_expr >= start,
                ym_expr <= end,
                AssemblyCostItem.part_number.like(pattern, escape="\\"),
            )
        )
        q = apply_assembly_cost_scope(
            q,
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        q = q.order_by(
            AssemblyCost.year.desc(),
            AssemblyCost.month.desc(),
            AssemblyCost.is_tree_root.desc(),
            AssemblyCostItem.id.desc(),
        ).limit(limit)
        return [_line_from_card_item(card, item) for card, item in q.all()]

    def _query_composition_lines_impl(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        part_number: str | None,
        limit: int,
    ) -> list[L0CompositionLineRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = AssemblyCost.year * 100 + AssemblyCost.month
        q = (
            db.query(AssemblyCost, AssemblyCostItem)
            .join(
                AssemblyCostItem,
                AssemblyCostItem.assembly_cost_id == AssemblyCost.id,
            )
            .filter(
                ym_expr >= start,
                ym_expr <= end,
                AssemblyCost.is_tree_root.is_(True),
                AssemblyCost.should_cost > 0,
                or_(
                    AssemblyCostItem.line_amount >= 50,
                    AssemblyCostItem.effective_qty >= 10000,
                ),
            )
        )
        q = apply_assembly_cost_scope(
            q,
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(AssemblyCost.part_number.like(pattern, escape="\\"))
        q = q.order_by(AssemblyCostItem.line_amount.desc()).limit(limit)
        return [_line_from_card_item(card, item) for card, item in q.all()]

    def _query_standard_part_price_lines_impl(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        min_unit_price: Decimal,
        supply_types: tuple[str, ...],
        name_keys: tuple[str, ...],
        part_number: str | None,
        limit: int,
    ) -> list[L0CompositionLineRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = AssemblyCost.year * 100 + AssemblyCost.month
        name_filters = [AssemblyCostItem.part_name.contains(key) for key in name_keys]
        q = (
            db.query(AssemblyCost, AssemblyCostItem)
            .join(
                AssemblyCostItem,
                AssemblyCostItem.assembly_cost_id == AssemblyCost.id,
            )
            .filter(
                ym_expr >= start,
                ym_expr <= end,
                AssemblyCost.is_tree_root.is_(True),
                AssemblyCostItem.cost_source == "annual",
                AssemblyCostItem.unit_price >= min_unit_price,
                or_(
                    AssemblyCostItem.supply_type.in_(list(supply_types)),
                    *name_filters,
                ),
            )
        )
        q = apply_assembly_cost_scope(
            q,
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(AssemblyCost.part_number.like(pattern, escape="\\"))
        q = q.order_by(AssemblyCostItem.unit_price.desc()).limit(limit)
        return [_line_from_card_item(card, item) for card, item in q.all()]
