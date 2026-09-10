"""总成核价成本还原 — 只读装配，不算价。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.money import Q4, quantize_money
from app.exceptions.base import NotFoundException
from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.bom.node import BomNode
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.costing.steel_price import SteelPrice
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.gauge_fee import StampingGaugeFee
from app.models.stamping.process_fee import StampingProcessFee
from app.models.yishiyiyi.scrap_price import StampingScrapPrice
from app.models.yishiyiyi.steel_base_price import SteelBasePrice
from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.repositories.bom.bom_repository import BomNodeRepository
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostRepository,
)
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.file_trace.upload_file_repository import UploadFileRepository
from app.repositories.stamping.die_fee_repository import StampingDieFeeRepository
from app.repositories.stamping.gauge_fee_repository import StampingGaugeFeeRepository
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.base_price.steel_base_price_repository import (
    SteelBasePriceRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.schemas.vo.assembly_cost_restore_vo import (
    AssemblyCostRestoreVO,
    RestoreAnnualVO,
    RestoreDieOpVO,
    RestoreDocumentRefVO,
    RestoreExceptionVO,
    RestoreIdentityCheckVO,
    RestoreIndirectLineVO,
    RestoreMaterialNodeVO,
    RestoreProcessOpVO,
    RestoreStampingVO,
    RestoreSteelVO,
    RestoreSupplierCostVO,
    RestoreWeldingLineVO,
    RestoreWeldingVO,
)
from app.services.costing.assembly_cost.codes import (
    card_short_code,
    tree_item_short_code,
)
from app.services.costing.assembly_cost.restore.labels import (
    HIGHLIGHT_GRAND_TOTAL,
    HIGHLIGHT_TOTAL_COST,
    INDIRECT_KIND_LABELS,
    INDIRECT_UNIT_TRANSPORT,
    INDIRECT_WAREHOUSE_BUNDLING,
    cost_source_label,
    document_category_label,
    indirect_kind,
)
from app.services.settings.system.settings_service import SettingsService


def _money(value: object | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return quantize_money(value, Q4, allow_negative=True)


def _opt_money(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return quantize_money(value, Q4, allow_negative=True)


def _match(left: Decimal, right: Decimal) -> bool:
    return _money(left) == _money(right)


class AssemblyCostRestoreService:
    def __init__(self) -> None:
        self.cost_repo = AssemblyCostRepository()
        self.node_repo = BomNodeRepository()
        self.stamping_repo = StampingPartCostRepository()
        self.annual_repo = BomAnnualPartPriceRepository()
        self.welding_repo = BomWeldingFeeRepository()
        self.process_fee_repo = StampingProcessFeeRepository()
        self.die_fee_repo = StampingDieFeeRepository()
        self.gauge_fee_repo = StampingGaugeFeeRepository()
        self.steel_repo = SteelPriceRepository()
        self.scrap_repo = StampingScrapPriceRepository()
        self.base_price_repo = SteelBasePriceRepository()
        self.packaging_repo = BomPackagingTransportFeeRepository()
        self.upload_file_repo = UploadFileRepository()
        self.settings_service = SettingsService()

    def get_restore_by_part(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        part_number: str,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        view: str = "finance",
    ) -> AssemblyCostRestoreVO:
        cost_id = self._resolve_cost_id(
            db,
            year=year,
            month=month,
            part_number=part_number.strip(),
            location=location.strip() if location else None,
            vehicle_model=vehicle_model.strip() if vehicle_model else None,
            bom_version=bom_version.strip() if bom_version else None,
            view=view,
        )
        return self.get_restore(db, cost_id, view=view)

    def _resolve_cost_id(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        part_number: str,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        view: str,
    ) -> int:
        rows = self.cost_repo.list_by_part_scope(
            db,
            year=year,
            month=month,
            part_number=part_number,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if not rows:
            raise NotFoundException(f"没有核价卡：{year}年{month:02d}月 {part_number}")
        picked = self._pick_card(rows, view=view)
        return picked.id

    def _pick_card(self, rows: list[AssemblyCost], *, view: str) -> AssemblyCost:
        if len(rows) == 1:
            return rows[0]
        if view == "finance":
            roots = [row for row in rows if row.is_tree_root]
            if roots:
                return roots[0]
        else:
            objects = [row for row in rows if row.procurement_object_id is not None]
            if objects:
                return objects[0]
        return rows[0]

    def get_restore(
        self,
        db: Session,
        cost_id: int,
        *,
        view: str = "finance",
    ) -> AssemblyCostRestoreVO:
        card = self.cost_repo.get_by_id(db, cost_id)
        if card is None:
            raise NotFoundException("记录不存在")
        report_view = "procurement" if view == "procurement" else "finance"
        items = sorted(card.items, key=lambda row: (row.sort_no, row.id))
        short = card_short_code(
            part_number=card.part_number,
            level=card.level,
            view=report_view,
        )
        exceptions: list[RestoreExceptionVO] = []
        tree_from_snapshot, parent_by_id, snapshot_nodes = self._snapshot_parents(
            db, card, exceptions
        )
        children_by_parent: dict[int | None, list[BomNode]] = defaultdict(list)
        for snap in snapshot_nodes:
            children_by_parent[snap.parent_id].append(snap)
        assembly_ids = [
            snap.id
            for snap in snapshot_nodes
            if snap.id != card.source_node_id and children_by_parent.get(snap.id)
        ]
        sibling_by_node = self._sibling_cards(db, card, items, extra_node_ids=assembly_ids)
        stamping_by_part = self._load_stamping(db, card, items)
        annual_by_part = self._load_annual(db, card, items)
        process_by_id, die_by_id, gauge_ids = self._collect_fee_ids(stamping_by_part)
        process_map = {row.id: row for row in self.process_fee_repo.list_by_ids(db, process_by_id)}
        die_map = {row.id: row for row in self.die_fee_repo.list_by_ids(db, die_by_id)}
        gauge_map = {row.id: row for row in self.gauge_fee_repo.list_by_ids(db, list(gauge_ids))}
        steel_ids = [
            int(row.steel_price_id)
            for rows in stamping_by_part.values()
            for row in rows
            if row.steel_price_id
        ]
        steel_map = {row.id: row for row in self.steel_repo.list_by_ids(db, steel_ids)}
        base_price_ids = [int(row.base_price_id) for row in steel_map.values() if row.base_price_id]
        base_price_map = {
            row.id: row for row in self.base_price_repo.list_by_ids(db, base_price_ids)
        }
        scrap_ids = [
            int(row.scrap_price_id)
            for rows in stamping_by_part.values()
            for row in rows
            if row.scrap_price_id
        ]
        scrap_map = {row.id: row for row in self.scrap_repo.list_by_ids(db, scrap_ids)}

        material_nodes: list[RestoreMaterialNodeVO] = []
        documents: list[RestoreDocumentRefVO] = []
        for item in items:
            material_nodes.append(
                self._build_material_node(
                    db=db,
                    item=item,
                    view=report_view,
                    tree_from_snapshot=tree_from_snapshot,
                    parent_by_id=parent_by_id,
                    stamping_by_part=stamping_by_part,
                    annual_by_part=annual_by_part,
                    process_map=process_map,
                    die_map=die_map,
                    gauge_map=gauge_map,
                    steel_map=steel_map,
                    base_price_map=base_price_map,
                    scrap_map=scrap_map,
                    exceptions=exceptions,
                    documents=documents,
                )
            )

        if tree_from_snapshot:
            material_nodes = self._weave_sub_assemblies(
                card=card,
                item_nodes=material_nodes,
                snapshot_nodes=snapshot_nodes,
                parent_by_id=parent_by_id,
                sibling_by_node=sibling_by_node,
                view=report_view,
            )

        welding = self._build_welding(db, card, exceptions)
        rows = self.packaging_repo.list_by_location_year(db, location=card.location, year=card.year)
        packaging = next((row for row in rows if row.part_number == card.part_number), None)
        indirects = self._build_indirects(card, packaging, exceptions)
        if packaging is not None and packaging.excel_filename:
            self._add_document(
                documents,
                file_category="bom_packaging_transport_fee",
                filename=packaging.excel_filename,
                excel_row=packaging.excel_row,
                short_code=short,
            )

        identity = self._identity_checks(card, items, exceptions)
        highlight_amount = card.total_amount if report_view == "procurement" else card.grand_total
        highlight_label = (
            HIGHLIGHT_TOTAL_COST if report_view == "procurement" else HIGHLIGHT_GRAND_TOTAL
        )

        return AssemblyCostRestoreVO(
            view=report_view,
            highlight_label=highlight_label,
            highlight_amount=_money(highlight_amount),
            id=card.id,
            year=card.year,
            month=card.month,
            location=card.location,
            vehicle_model=card.vehicle_model,
            bom_version=card.bom_version,
            part_number=card.part_number,
            part_name=card.part_name,
            short_code=short,
            calc_status=card.calc_status,
            audit_status=card.audit_status,
            calculated_at=card.calculated_at,
            stamping_amount=_money(card.stamping_amount),
            purchased_amount=_money(card.purchased_amount),
            bundle_amount=_money(card.bundle_amount),
            welding_amount=_money(card.welding_amount),
            total_amount=_money(card.total_amount),
            should_cost=_money(card.should_cost),
            indirect_amount=_money(card.indirect_amount),
            grand_total=_money(card.grand_total),
            identity_checks=identity,
            exceptions=exceptions,
            material_nodes=material_nodes,
            welding=welding,
            indirects=indirects,
            documents=self._merge_documents(documents),
            company_name=self.settings_service.get_config(db).company_name or "",
            calculated_by=(
                (
                    getattr(card, "updated_by", None) or getattr(card, "created_by", None) or ""
                ).strip()
            ),
        )

    def _snapshot_parents(
        self,
        db: Session,
        card: AssemblyCost,
        exceptions: list[RestoreExceptionVO],
    ) -> tuple[bool, dict[int, int | None], list[BomNode]]:
        empty: list[BomNode] = []
        if card.bom_snapshot_id is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="identity",
                    message="当时的材料清单找不到了",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return False, {}, empty
        nodes = self.node_repo.list_by_snapshot(db, card.bom_snapshot_id)
        if not nodes:
            exceptions.append(
                RestoreExceptionVO(
                    kind="identity",
                    message="当时的材料清单找不到了",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return False, {}, empty
        by_id = {node.id: node for node in nodes}
        parent_map = {node.id: node.parent_id for node in nodes}
        if card.source_node_id not in by_id:
            exceptions.append(
                RestoreExceptionVO(
                    kind="identity",
                    message="材料清单改过了，要重新算价",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return False, parent_map, nodes
        return True, parent_map, nodes

    def _indent_level(
        self,
        item: AssemblyCostItem,
        *,
        tree_from_snapshot: bool,
        parent_by_id: dict[int, int | None],
    ) -> int:
        if not tree_from_snapshot or item.bom_node_id is None:
            return int(item.node_level or 0)
        depth = 0
        node_id: int | None = item.bom_node_id
        seen: set[int] = set()
        while node_id is not None and node_id in parent_by_id and node_id not in seen:
            seen.add(node_id)
            node_id = parent_by_id.get(node_id)
            depth += 1
            if depth > 40:
                break
        return max(0, depth - 1) if depth else int(item.node_level or 0)

    def _indent_from_card(
        self,
        node_id: int | None,
        card_source_id: int,
        parent_by_id: dict[int, int | None],
    ) -> int:
        if node_id is None:
            return 0
        depth = 0
        current: int | None = node_id
        seen: set[int] = set()
        while current is not None and current != card_source_id:
            if current in seen:
                break
            seen.add(current)
            current = parent_by_id.get(current)
            depth += 1
            if depth > 40:
                break
        return max(0, depth - 1)

    def _weave_sub_assemblies(
        self,
        *,
        card: AssemblyCost,
        item_nodes: list[RestoreMaterialNodeVO],
        snapshot_nodes: list[BomNode],
        parent_by_id: dict[int, int | None],
        sibling_by_node: dict[int, AssemblyCost],
        view: str,
    ) -> list[RestoreMaterialNodeVO]:
        children_by_parent: dict[int | None, list[BomNode]] = defaultdict(list)
        for snap in snapshot_nodes:
            children_by_parent[snap.parent_id].append(snap)
        for siblings in children_by_parent.values():
            siblings.sort(key=lambda row: (row.sort_no, row.id))
        by_bom_id = {node.bom_node_id: node for node in item_nodes if node.bom_node_id is not None}
        root_node = next((row for row in snapshot_nodes if row.id == card.source_node_id), None)
        root_seq = ""
        if root_node is not None and root_node.seq_no is not None:
            root_seq = str(root_node.seq_no)
        ordered: list[RestoreMaterialNodeVO] = []
        used: set[int] = set()
        sort_no = 0

        def emit(node: RestoreMaterialNodeVO, bom_id: int, seq_label: str) -> None:
            nonlocal sort_no
            sort_no += 1
            indent = self._indent_from_card(bom_id, card.source_node_id, parent_by_id)
            ordered.append(
                node.model_copy(
                    update={"sort_no": sort_no, "indent_level": indent, "seq_label": seq_label}
                )
            )
            used.add(bom_id)

        def walk(parent_id: int, path_qty: Decimal, parent_seq: str) -> None:
            nonlocal sort_no
            for index, child in enumerate(children_by_parent.get(parent_id, []), start=1):
                child_qty = path_qty * (
                    Decimal(str(child.qty)) if child.qty is not None else Decimal("1")
                )
                seq_label = f"{parent_seq}-{index}" if parent_seq else str(index)
                kids = children_by_parent.get(child.id, [])
                if child.id in by_bom_id:
                    emit(by_bom_id[child.id], child.id, seq_label)
                elif kids:
                    sort_no += 1
                    ordered.append(
                        self._sub_assembly_node(
                            card=card,
                            bom_node=child,
                            path_qty=child_qty,
                            sort_no=sort_no,
                            seq_label=seq_label,
                            sibling=sibling_by_node.get(child.id),
                            item_nodes=item_nodes,
                            parent_by_id=parent_by_id,
                            view=view,
                        )
                    )
                    used.add(child.id)
                if kids:
                    walk(child.id, child_qty, seq_label)

        walk(card.source_node_id, Decimal("1"), root_seq)
        for leftover in item_nodes:
            if leftover.bom_node_id is None or leftover.bom_node_id not in used:
                sort_no += 1
                ordered.append(leftover.model_copy(update={"sort_no": sort_no}))
        return ordered

    def _sub_assembly_node(
        self,
        *,
        card: AssemblyCost,
        bom_node: BomNode,
        path_qty: Decimal,
        sort_no: int,
        seq_label: str,
        sibling: AssemblyCost | None,
        item_nodes: list[RestoreMaterialNodeVO],
        parent_by_id: dict[int, int | None],
        view: str,
    ) -> RestoreMaterialNodeVO:
        indent = self._indent_from_card(bom_node.id, card.source_node_id, parent_by_id)
        if sibling is not None:
            unit = _money(sibling.total_amount)
            material_amt = _money(sibling.material_amount)
            welding_amt = _money(sibling.welding_amount)
            line = _money(unit * path_qty)
        else:
            material_amt = _money(
                sum(
                    (
                        node.line_amount
                        for node in item_nodes
                        if node.bom_node_id
                        and self._is_bom_descendant(node.bom_node_id, bom_node.id, parent_by_id)
                    ),
                    Decimal("0"),
                )
            )
            welding_amt = Decimal("0")
            unit = material_amt
            line = material_amt
        return RestoreMaterialNodeVO(
            sort_no=sort_no,
            indent_level=indent,
            node_level=int(bom_node.level or 0),
            bom_node_id=bom_node.id,
            part_number=bom_node.part_number,
            part_name=bom_node.part_name,
            short_code=card_short_code(
                part_number=bom_node.part_number,
                level=bom_node.level,
                view=view,
            ),
            seq_label=seq_label,
            node_role=bom_node.node_role,
            supply_type=None,
            cost_source="sub_assembly",
            cost_source_label=cost_source_label("sub_assembly"),
            unit_price=unit,
            effective_qty=path_qty,
            line_amount=line,
            assembly_material_amount=material_amt,
            assembly_welding_amount=welding_amt,
        )

    def _is_bom_descendant(
        self,
        node_id: int,
        ancestor_id: int,
        parent_by_id: dict[int, int | None],
    ) -> bool:
        current: int | None = node_id
        seen: set[int] = set()
        while current is not None:
            if current == ancestor_id:
                return True
            if current in seen:
                return False
            seen.add(current)
            current = parent_by_id.get(current)
        return False

    def _sibling_cards(
        self,
        db: Session,
        card: AssemblyCost,
        items: list[AssemblyCostItem],
        extra_node_ids: list[int] | None = None,
    ) -> dict[int, AssemblyCost]:
        node_ids = [item.bom_node_id for item in items if item.bom_node_id]
        if extra_node_ids:
            node_ids.extend(extra_node_ids)
        rows = self.cost_repo.list_by_scope_source_nodes(
            db,
            year=card.year,
            month=card.month,
            location=card.location,
            vehicle_model=card.vehicle_model,
            bom_version=card.bom_version,
            source_node_ids=node_ids,
        )
        found: dict[int, AssemblyCost] = {}
        for row in rows:
            if row.id == card.id:
                continue
            found[row.source_node_id] = row
        return found

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
            stamping_vo = self._build_stamping(
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
            indent_level=self._indent_level(
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

    def _build_stamping(
        self,
        *,
        db: Session,
        item: AssemblyCostItem,
        short: str,
        rows: list[StampingPartCost],
        process_map: dict[int, StampingProcessFee],
        die_map: dict[int, StampingDieFee],
        gauge_map: dict[int, StampingGaugeFee],
        steel_map: dict[int, SteelPrice],
        base_price_map: dict[int, SteelBasePrice],
        scrap_map: dict[int, StampingScrapPrice],
        exceptions: list[RestoreExceptionVO],
        documents: list[RestoreDocumentRefVO],
    ) -> RestoreStampingVO:
        if not rows:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
            return RestoreStampingVO(record_missing=True, missing_reason="找不到当时的价")
        costs = {_money(row.unit_cost) for row in rows}
        note = None
        if len(rows) > 1 and len(costs) == 1:
            note = "几家工厂价一样"
        picked = rows[0]
        process_row = process_map.get(picked.process_fee_id) if picked.process_fee_id else None
        die_row = die_map.get(picked.die_fee_id) if picked.die_fee_id else None
        if picked.process_fee_id and process_row is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的工序价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        if picked.die_fee_id and die_row is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的模具价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        steel = self._build_steel(
            picked, steel_map, base_price_map, exceptions, short, item.part_number
        )
        scrap_exists = bool(picked.scrap_price_id and picked.scrap_price_id in scrap_map)
        if picked.scrap_price_id and not scrap_exists:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的废料价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        process_ops = self._process_ops(process_row)
        die_ops = self._die_ops(die_row)
        part_filename = (picked.excel_filename or "").strip()
        if part_filename:
            self._add_document(
                documents,
                file_category="stamping_part",
                filename=part_filename,
                excel_row=picked.excel_row,
                short_code=short,
            )
        process_filename = (
            (process_row.excel_filename or "").strip() if process_row is not None else ""
        )
        if process_filename and process_filename != part_filename:
            self._add_document(
                documents,
                file_category="stamping_process_fee",
                filename=process_filename,
                excel_row=None,
                short_code=short,
            )
        if process_row is not None:
            self._add_tonnage_documents(
                db,
                documents,
                location=process_row.location,
                year=process_row.year,
                short_code=short,
            )
        if die_row is not None and die_row.excel_filename:
            self._add_document(
                documents,
                file_category="stamping_die",
                filename=die_row.excel_filename,
                excel_row=None,
                short_code=short,
            )
        if steel is not None and steel.base_excel_filename:
            self._add_document(
                documents,
                file_category="steel_base_price",
                filename=steel.base_excel_filename,
                excel_row=steel.base_excel_row,
                short_code=short,
            )
        if steel is not None and steel.thickness_excel_filename:
            self._add_document(
                documents,
                file_category="steel_thickness_policy",
                filename=steel.thickness_excel_filename,
                excel_row=steel.thickness_excel_row,
                short_code=short,
            )
        gauge_exists = bool(picked.gauge_fee_id and picked.gauge_fee_id in gauge_map)
        if picked.gauge_fee_id and not gauge_exists:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的检具价",
                    short_code=short,
                    part_number=item.part_number,
                )
            )
        return RestoreStampingVO(
            record_id=picked.id,
            record_missing=False,
            stamping_supplier=picked.stamping_supplier,
            same_unit_cost_note=note,
            unit_cost=_opt_money(picked.unit_cost),
            direct_cost=_opt_money(picked.direct_cost),
            formula_version=picked.formula_version,
            is_offal_nested=bool(picked.is_offal_nested),
            offal_source=picked.offal_source,
            material_amount_sheet=_opt_money(picked.material_amount_sheet),
            loss_scrap_deduction=_opt_money(picked.loss_scrap_deduction),
            process_scrap_deduction=_opt_money(picked.process_scrap_deduction),
            material_net_per_part=_opt_money(picked.material_net_per_part),
            blank_weight_kg=Decimal(str(picked.blank_weight_kg))
            if picked.blank_weight_kg is not None
            else None,
            finished_total_kg=_opt_money(picked.finished_total_kg),
            scrap_weight_kg=_opt_money(picked.scrap_weight_kg),
            density=_opt_money(picked.density),
            material_loss_rate=Decimal(str(picked.material_loss_rate))
            if picked.material_loss_rate is not None
            else None,
            scrap_recovery_rate=Decimal(str(picked.scrap_recovery_rate))
            if picked.scrap_recovery_rate is not None
            else None,
            sheet_length=_opt_money(picked.sheet_length),
            sheet_width=_opt_money(picked.sheet_width),
            thickness=_opt_money(picked.thickness),
            parts_per_sheet=picked.parts_per_sheet,
            swing_shear_fee_per_ton=_opt_money(picked.swing_shear_fee_per_ton),
            steel=steel,
            scrap_price_id=picked.scrap_price_id,
            scrap_ton_price=_opt_money(picked.scrap_ton_price),
            scrap_record_exists=scrap_exists or picked.scrap_price_id is None,
            process_fee_id=picked.process_fee_id,
            process_fee_amount=_opt_money(picked.process_fee_amount),
            process_excel_filename=process_row.excel_filename if process_row is not None else None,
            process_ops=process_ops,
            die_fee_id=picked.die_fee_id,
            die_fee_amount=_opt_money(picked.die_fee_amount),
            die_system_fee=_opt_money(die_row.die_fee) if die_row is not None else None,
            die_adjustment_amount=_opt_money(die_row.adjustment_amount)
            if die_row is not None
            else None,
            die_unit_price=_opt_money(die_row.unit_price) if die_row is not None else None,
            die_allocation_qty=_opt_money(die_row.allocation_qty) if die_row is not None else None,
            die_price_kind=die_row.price_kind if die_row is not None else None,
            die_excel_filename=die_row.excel_filename if die_row is not None else None,
            die_ops=die_ops,
            gauge_fee_id=picked.gauge_fee_id,
            gauge_fee_amount=_opt_money(picked.gauge_fee_amount),
            gauge_record_exists=gauge_exists or picked.gauge_fee_id is None,
            finished_finance_fee=_opt_money(picked.finished_finance_fee),
            finished_management_fee=_opt_money(picked.finished_management_fee),
            finished_warehouse_packaging_fee=_opt_money(picked.finished_warehouse_packaging_fee),
            finished_pretax_profit_fee=_opt_money(picked.finished_pretax_profit_fee),
            excel_filename=picked.excel_filename,
            excel_row=picked.excel_row,
        )

    def _build_steel(
        self,
        picked: StampingPartCost,
        steel_map: dict[int, SteelPrice],
        base_price_map: dict[int, SteelBasePrice],
        exceptions: list[RestoreExceptionVO],
        short: str,
        part_number: str,
    ) -> RestoreSteelVO:
        if picked.steel_price_id is None:
            return RestoreSteelVO(
                steel_mill=picked.steel_mill,
                steel_ton_price=_opt_money(picked.steel_ton_price),
                record_exists=False,
            )
        row = steel_map.get(picked.steel_price_id)
        if row is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的钢价",
                    short_code=short,
                    part_number=part_number,
                )
            )
            return RestoreSteelVO(
                steel_mill=picked.steel_mill,
                steel_ton_price=_opt_money(picked.steel_ton_price),
                steel_price_id=picked.steel_price_id,
                record_exists=False,
                missing_reason="找不到当时的钢价",
            )
        base_row = base_price_map.get(row.base_price_id) if row.base_price_id else None
        filename = None
        excel_row = None
        if base_row is not None:
            filename = base_row.excel_filename
            excel_row = base_row.excel_row
        elif row.base_excel_filename:
            filename = row.base_excel_filename
            excel_row = row.base_excel_row
        return RestoreSteelVO(
            steel_mill=picked.steel_mill or row.steel_mill,
            steel_ton_price=_opt_money(picked.steel_ton_price),
            steel_price_id=picked.steel_price_id,
            record_exists=True,
            base_price=_opt_money(row.base_price),
            thickness_adjustment=_opt_money(row.thickness_adjustment),
            width_adjustment=_opt_money(row.width_adjustment),
            zinc_adjustment=_opt_money(row.zinc_adjustment),
            processing_fee=_opt_money(row.processing_fee),
            other_adjustment=_opt_money(row.other_adjustment),
            final_price_per_ton=_opt_money(row.final_price_per_ton),
            base_excel_filename=filename,
            base_excel_row=excel_row,
            thickness_excel_filename=row.thickness_excel_filename,
            thickness_excel_row=row.thickness_excel_row,
        )

    def _process_ops(self, process_row: StampingProcessFee | None) -> list[RestoreProcessOpVO]:
        if process_row is None:
            return []
        ops: list[RestoreProcessOpVO] = []
        for op in process_row.process_items:
            ops.append(
                RestoreProcessOpVO(
                    process_seq=op.process_seq,
                    process_code=op.process_code,
                    original_tonnage=op.original_tonnage,
                    resolved_tonnage=op.resolved_tonnage,
                    tonnage_source=op.tonnage_source,
                    inherited_from_part_number=op.inherited_from_part_number,
                    inherited_from_process_seq=op.inherited_from_process_seq,
                    cost_ratio=_opt_money(op.cost_ratio),
                    price_per_stroke=_opt_money(op.price_per_stroke),
                    line_fee=_money(op.line_fee),
                    basis_text=op.basis_text,
                )
            )
        return ops

    def _die_ops(self, die_row: StampingDieFee | None) -> list[RestoreDieOpVO]:
        if die_row is None:
            return []
        return [
            RestoreDieOpVO(
                process_seq=op.process_seq,
                process_code=op.process_code,
                estimated_weight_t=_opt_money(op.estimated_weight_t),
                alloc_ratio=_opt_money(op.alloc_ratio),
                die_sets=op.die_sets,
                unit_price=_money(op.unit_price),
                allocation_qty=_opt_money(op.allocation_qty),
                price_kind=op.price_kind,
                line_die_fee=_money(op.line_die_fee),
                basis_text=op.basis_text,
            )
            for op in die_row.items
        ]

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

    def _build_welding(
        self,
        db: Session,
        card: AssemblyCost,
        exceptions: list[RestoreExceptionVO],
    ) -> RestoreWeldingVO:
        if card.welding_fee_id is None:
            return RestoreWeldingVO(
                has_record=False,
                message="没有焊接",
                card_level=card.level,
            )
        fee = self.welding_repo.get_by_id(db, card.welding_fee_id)
        if fee is None:
            exceptions.append(
                RestoreExceptionVO(
                    kind="broken_link",
                    message="找不到当时的焊接价",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
            return RestoreWeldingVO(
                has_record=False,
                message="找不到当时的价",
                welding_fee_id=card.welding_fee_id,
                card_level=card.level,
            )
        mismatch = fee.level != card.level
        if mismatch:
            exceptions.append(
                RestoreExceptionVO(
                    kind="warning",
                    message=f"焊接层级对不上（表上是 {fee.level}，本件是 {card.level}），先用这条金额",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
        if fee.calc_status != "ok" or (fee.missing_price_count or 0) > 0:
            exceptions.append(
                RestoreExceptionVO(
                    kind="welding",
                    message=fee.calc_message or "焊接有缺价",
                    short_code=card_short_code(
                        part_number=card.part_number, level=card.level, view="finance"
                    ),
                    part_number=card.part_number,
                )
            )
        items = [
            RestoreWeldingLineVO(
                line_no=line.line_no,
                process_token=line.process_token,
                standard_process_name=line.standard_process_name,
                process_qty=Decimal(str(line.process_qty)),
                unit_price=_opt_money(line.unit_price),
                line_fee=_opt_money(line.line_fee),
                match_status=line.match_status,
                source_breakdown_line_id=line.source_breakdown_line_id,
            )
            for line in fee.items
        ]
        final_amount = fee.final_welding_fee
        if final_amount is None:
            final_amount = fee.total_welding_fee
        return RestoreWeldingVO(
            has_record=True,
            welding_fee_id=fee.id,
            weld_info_raw=fee.weld_info_raw,
            total_welding_fee=_opt_money(fee.total_welding_fee),
            other_fee=_opt_money(fee.other_fee),
            final_welding_fee=_opt_money(final_amount),
            calc_status=fee.calc_status,
            fee_level=fee.level,
            card_level=card.level,
            level_mismatch=mismatch,
            items=items,
        )

    def _build_indirects(
        self,
        card: AssemblyCost,
        packaging: BomPackagingTransportFee | None,
        exceptions: list[RestoreExceptionVO],
    ) -> list[RestoreIndirectLineVO]:
        lines: list[RestoreIndirectLineVO] = []
        match_key = f"{card.location} · {card.year} · {card.part_number}"
        for row in sorted(card.indirects, key=lambda item: (item.sort_no, item.id)):
            kind = indirect_kind(row.code)
            note = None
            if (
                row.code in {INDIRECT_UNIT_TRANSPORT, INDIRECT_WAREHOUSE_BUNDLING}
                and packaging is None
            ):
                note = "没有包装表这一行，所以是 0"
            lines.append(
                RestoreIndirectLineVO(
                    code=row.code,
                    label=INDIRECT_KIND_LABELS.get(row.code, row.label),
                    kind=kind,
                    amount=_money(row.amount),
                    rate=Decimal(str(row.rate)) if row.rate is not None else None,
                    base_amount=_opt_money(row.base_amount),
                    match_key=match_key if kind == "direct" else None,
                    note=note,
                )
            )
        return lines

    def _identity_checks(
        self,
        card: AssemblyCost,
        items: list[AssemblyCostItem],
        exceptions: list[RestoreExceptionVO],
    ) -> list[RestoreIdentityCheckVO]:
        by_source: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in items:
            if item.cost_source == "skipped_by_bundle":
                continue
            by_source[item.cost_source] += _money(item.line_amount)
        stamp_sum = by_source["stamping"]
        purchased_sum = by_source["annual"]
        bundle_sum = by_source["bundle"]
        material_sum = _money(stamp_sum + purchased_sum + bundle_sum)
        total_sum = _money(
            material_sum + _money(card.welding_amount) + _money(card.welding_other_fee)
        )
        indirect_sum = _money(sum((_money(row.amount) for row in card.indirects), Decimal("0")))
        grand_sum = _money(total_sum + indirect_sum)
        checks = [
            RestoreIdentityCheckVO(
                code="stamping",
                label="自制冲压",
                recorded=_money(card.stamping_amount),
                summed=stamp_sum,
                is_match=_match(card.stamping_amount, stamp_sum),
            ),
            RestoreIdentityCheckVO(
                code="purchased",
                label="外购件",
                recorded=_money(card.purchased_amount),
                summed=purchased_sum,
                is_match=_match(card.purchased_amount, purchased_sum),
            ),
            RestoreIdentityCheckVO(
                code="bundle",
                label="一口价",
                recorded=_money(card.bundle_amount),
                summed=bundle_sum,
                is_match=_match(card.bundle_amount, bundle_sum),
            ),
            RestoreIdentityCheckVO(
                code="material",
                label="零件合计",
                recorded=_money(card.material_amount),
                summed=material_sum,
                is_match=_match(card.material_amount, material_sum),
            ),
            RestoreIdentityCheckVO(
                code="total",
                label=HIGHLIGHT_TOTAL_COST,
                recorded=_money(card.total_amount),
                summed=total_sum,
                is_match=_match(card.total_amount, total_sum),
            ),
            RestoreIdentityCheckVO(
                code="should",
                label=f"{HIGHLIGHT_TOTAL_COST}（两处）",
                recorded=_money(card.should_cost),
                summed=_money(card.total_amount),
                is_match=_match(card.should_cost, card.total_amount),
            ),
            RestoreIdentityCheckVO(
                code="indirect",
                label="摊入费用",
                recorded=_money(card.indirect_amount),
                summed=indirect_sum,
                is_match=_match(card.indirect_amount, indirect_sum),
            ),
            RestoreIdentityCheckVO(
                code="grand",
                label=HIGHLIGHT_GRAND_TOTAL,
                recorded=_money(card.grand_total),
                summed=_money(_money(card.total_amount) + _money(card.indirect_amount)),
                is_match=_match(
                    card.grand_total, _money(card.total_amount) + _money(card.indirect_amount)
                ),
            ),
        ]
        del grand_sum
        for check in checks:
            if not check.is_match:
                exceptions.append(
                    RestoreExceptionVO(
                        kind="identity",
                        message=f"{check.label}加总对不上",
                        short_code=card_short_code(
                            part_number=card.part_number, level=card.level, view="finance"
                        ),
                        part_number=card.part_number,
                    )
                )
        return checks

    def _add_tonnage_documents(
        self,
        db: Session,
        documents: list[RestoreDocumentRefVO],
        *,
        location: str,
        year: int,
        short_code: str,
    ) -> None:
        rows = self.upload_file_repo.list_active_by_scope(
            db,
            file_category="stamping_tonnage_price",
            location=location,
            year=year,
        )
        for row in rows:
            filename = (row.original_filename or "").strip()
            if not filename:
                continue
            self._add_document(
                documents,
                file_category="stamping_tonnage_price",
                filename=filename,
                excel_row=None,
                short_code=short_code,
            )

    def _add_document(
        self,
        documents: list[RestoreDocumentRefVO],
        *,
        file_category: str,
        filename: str,
        excel_row: int | None,
        short_code: str,
    ) -> None:
        documents.append(
            RestoreDocumentRefVO(
                file_category=file_category,
                file_category_label=document_category_label(file_category),
                filename=filename,
                excel_row=excel_row,
                cited_short_codes=[short_code] if short_code else [],
            )
        )

    def _merge_documents(self, documents: list[RestoreDocumentRefVO]) -> list[RestoreDocumentRefVO]:
        grouped: dict[tuple[str, str, int | None], list[str]] = {}
        for doc in documents:
            key = (doc.file_category, doc.filename, doc.excel_row)
            codes = grouped.setdefault(key, [])
            for code in doc.cited_short_codes:
                if code not in codes:
                    codes.append(code)
        merged = [
            RestoreDocumentRefVO(
                file_category=category,
                file_category_label=document_category_label(category),
                filename=filename,
                excel_row=row,
                cited_short_codes=codes,
            )
            for (category, filename, row), codes in grouped.items()
        ]
        return sorted(merged, key=lambda doc: (doc.file_category, doc.filename, doc.excel_row or 0))
