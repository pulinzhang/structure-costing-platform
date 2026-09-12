"""还原取数：冲压核价、年价、加工/模具/检具 ID。

卡片字段拼装在 stamping.py / material.py；这里只按零件号批量查出。
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.models.costing.stamping_part_cost import StampingPartCost
from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)


class RestoreLookups:
    def __init__(
        self,
        stamping_repo: StampingPartCostRepository,
        annual_repo: BomAnnualPartPriceRepository,
    ) -> None:
        self.stamping_repo = stamping_repo
        self.annual_repo = annual_repo

    def _load_stamping(
        self,
        db: Session,
        card: AssemblyCost,
        items: list[AssemblyCostItem],
    ) -> dict[str, list[StampingPartCost]]:
        parts = [item.part_number for item in items if item.cost_source in {"stamping", "missing"}]
        rows = self.stamping_repo.list_success_by_part_numbers(
            db,
            year=card.year,
            month=card.month,
            location=card.location,
            vehicle_model=card.vehicle_model,
            part_numbers=parts,
        )
        grouped: dict[str, list[StampingPartCost]] = defaultdict(list)
        for row in rows:
            grouped[row.part_number].append(row)
        return grouped

    def _load_annual(
        self,
        db: Session,
        card: AssemblyCost,
        items: list[AssemblyCostItem],
    ) -> dict[str, BomAnnualPartPrice]:
        needed = {
            item.part_number
            for item in items
            if item.cost_source in {"annual", "bundle", "missing"}
        }
        if not needed:
            return {}
        rows = self.annual_repo.list_by_location_year(db, card.location, card.year)
        return {row.part_number: row for row in rows if row.part_number in needed}

    def _collect_fee_ids(
        self,
        stamping_by_part: dict[str, list[StampingPartCost]],
    ) -> tuple[list[int], list[int], set[int]]:
        process_ids: list[int] = []
        die_ids: list[int] = []
        gauge_ids: set[int] = set()
        seen_process: set[int] = set()
        seen_die: set[int] = set()
        for rows in stamping_by_part.values():
            for row in rows:
                if row.process_fee_id and row.process_fee_id not in seen_process:
                    seen_process.add(row.process_fee_id)
                    process_ids.append(row.process_fee_id)
                if row.die_fee_id and row.die_fee_id not in seen_die:
                    seen_die.add(row.die_fee_id)
                    die_ids.append(row.die_fee_id)
                if row.gauge_fee_id:
                    gauge_ids.add(row.gauge_fee_id)
        return process_ids, die_ids, gauge_ids
