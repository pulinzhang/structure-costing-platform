"""材料行：按 cost_source 决定展开冲压卡还是年价卡。

缺价（missing）会同时尝试冲压冲突与年价静默查找。
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.costing.steel_price import SteelPrice
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.gauge_fee import StampingGaugeFee
from app.models.stamping.process_fee import StampingProcessFee
from app.models.yishiyiyi.scrap_price import StampingScrapPrice
from app.models.yishiyiyi.steel_base_price import SteelBasePrice
from app.schemas.vo.assembly_cost_restore_vo import (
    RestoreAnnualVO,
    RestoreDocumentRefVO,
    RestoreExceptionVO,
    RestoreMaterialNodeVO,
    RestoreStampingVO,
    RestoreSupplierCostVO,
)
from app.services.costing.assembly_cost.codes import tree_item_short_code
from app.services.costing.assembly_cost.restore.labels import cost_source_label
from app.services.costing.assembly_cost.restore.money import _money, _opt_money
from app.services.costing.assembly_cost.restore.stamping import RestoreStamping
from app.services.costing.assembly_cost.restore.tree import RestoreTree


class RestoreMaterial:
    def __init__(self, tree: RestoreTree, stamping: RestoreStamping) -> None:
        self._tree = tree
        self._stamping = stamping

    def _build_material_node(
        self,
        *,
        db: Session,
        item: AssemblyCostItem,
        view: str,
        tree_from_snapshot: bool,
        parent_by_id: dict[int, int | None],
        stamping_by_part: dict[str, list[StampingPartCost]],
        annual_by_part: dict[str, BomAnnualPartPrice],
        process_map: dict[int, StampingProcessFee],
        die_map: dict[int, StampingDieFee],
        gauge_map: dict[int, StampingGaugeFee],
        steel_map: dict[int, SteelPrice],
        base_price_map: dict[int, SteelBasePrice],
        scrap_map: dict[int, StampingScrapPrice],
        exceptions: list[RestoreExceptionVO],
        documents: list[RestoreDocumentRefVO],
    ) -> RestoreMaterialNodeVO:
        short = tree_item_short_code(
            part_number=item.part_number,
            part_name=item.part_name,
            supply_type=item.supply_type,
            cost_source=item.cost_source,
            level=item.node_level,
            view=view,
        )
        stamping_vo = None
        annual_vo = None
        if item.cost_source == "stamping":
            stamping_vo = self._stamping._build_stamping(
                db=db,
                item=item,
                short=short,
                rows=stamping_by_part.get(item.part_number, []),
                process_map=process_map,
                die_map=die_map,
                gauge_map=gauge_map,
                steel_map=steel_map,
                base_price_map=base_price_map,
                scrap_map=scrap_map,
                exceptions=exceptions,
                documents=documents,
            )
        elif item.cost_source in {"annual", "bundle"}:
            annual_vo = self._build_annual(
                item=item,
                short=short,
                record=annual_by_part.get(item.part_number),
                exceptions=exceptions,
            )
        elif item.cost_source == "missing":
            exceptions.append(
                RestoreExceptionVO(
                    kind="missing",
                    message=item.match_hint or "既没有自己冲的价，也没有买来的价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
            rows = stamping_by_part.get(item.part_number, [])
            if len(rows) > 1:
                costs = {_money(row.unit_cost) for row in rows}
                if len(costs) > 1:
                    stamping_vo = RestoreStampingVO(
                        record_missing=True,
                        missing_reason="好几家工厂价不一样",
                        conflict_rows=[
                            RestoreSupplierCostVO(
                                stamping_supplier=row.stamping_supplier,
                                unit_cost=_money(row.unit_cost),
                            )
                            for row in rows
                        ],
                    )
            annual_vo = self._build_annual(
                item=item,
                short=short,
                record=annual_by_part.get(item.part_number),
                exceptions=exceptions,
                silent_if_missing=True,
            )
        return RestoreMaterialNodeVO(
            sort_no=item.sort_no,
            indent_level=self._tree._indent_level(
                item,
                tree_from_snapshot=tree_from_snapshot,
                parent_by_id=parent_by_id,
            ),
            node_level=item.node_level,
            bom_node_id=item.bom_node_id,
            part_number=item.part_number,
            part_name=item.part_name,
            short_code=short,
            node_role=item.node_role,
            supply_type=item.supply_type,
            cost_source=item.cost_source,
            cost_source_label=cost_source_label(item.cost_source),
            unit_price=_money(item.unit_price),
            effective_qty=Decimal(str(item.effective_qty)),
            line_amount=_money(item.line_amount),
            stamping=stamping_vo,
            annual=annual_vo,
        )

    def _build_annual(
        self,
        *,
        item: AssemblyCostItem,
        short: str,
        record: BomAnnualPartPrice | None,
        exceptions: list[RestoreExceptionVO],
        silent_if_missing: bool = False,
    ) -> RestoreAnnualVO | None:
        if record is None:
            if not silent_if_missing and item.cost_source in {"annual", "bundle"}:
                exceptions.append(
                    RestoreExceptionVO(
                        kind="broken_link",
                        message="找不到当时的价",
                        short_code=short,
                        part_number=item.part_number,
                    )
                )
                return RestoreAnnualVO(record_missing=True, missing_reason="找不到当时的价")
            return None
        return RestoreAnnualVO(
            record_missing=False,
            unit_price=_opt_money(record.unit_price),
            supplier_name=record.supplier_name,
            supply_type=record.supply_type,
        )
