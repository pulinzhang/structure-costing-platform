"""采购对象成本还原：按基地和年月取出对象，再展开各自的总成卡。"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.common.period import is_in_period
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode
from app.models.bom.procurement_object import BomProcurementObjectList
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.costing.assembly_cost.assembly_cost_calc_log_repository import (
    AssemblyCostCalcLogRepository,
)
from app.repositories.costing.assembly_cost.assembly_cost_repository import AssemblyCostRepository
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.stamping.die.repository import StampingDieProcessRepository
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.repositories.stamping.part.tailor_weld_blank import StampingTailorWeldBlankRepository
from app.repositories.stamping.process_fee.repository import StampingProcessFeeRepository
from app.schemas.dto.cost_restore_procurement_object_dto import CostRestoreProcurementObjectQuery
from app.schemas.vo.cost_restore_procurement_object_vo import (
    CostRestoreDefaultsVO,
    CostRestoreLineVO,
    CostRestoreScopeVO,
    CostRestoreVehicleChoiceVO,
)
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.bom.procurement_object.labels import KIND_LABELS
from app.services.costing.cost_restore.procurement_object.rows import (
    ObjectHit,
    RestoreBundle,
    RestoreLine,
    build_object_lines,
    line_to_vo,
    priced_part_number,
    slice_objects,
)
from app.services.costing.procurement_contract_report.qty import l0_node_of, vehicle_qty_from_l0
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.supplier.service import SupplierService
from app.services.masterdata.vehicle_model.service import VehicleModelService

_NO_LIST = "请先生成采购对象清单"


class CostRestoreProcurementObjectService:
    def __init__(self) -> None:
        self._lists = BomProcurementObjectRepository()
        self._nodes = BomNodeRepository()
        self._cards = AssemblyCostRepository()
        self._part_costs = StampingPartCostRepository()
        self._process_fees = StampingProcessFeeRepository()
        self._die_fees = StampingDieFeeRepository()
        self._die_processes = StampingDieProcessRepository()
        self._welding = BomWeldingFeeRepository()
        self._blanks = StampingTailorWeldBlankRepository()
        self._logs = AssemblyCostCalcLogRepository()
        self._locations = LocationService()
        self._vehicles = VehicleModelService()
        self._suppliers = SupplierService()

    def defaults(self, db: Session) -> CostRestoreDefaultsVO:
        logs, _total = self._logs.paginate(db, skip=0, limit=1)
        latest = logs[0] if logs else None
        catalog = self._vehicles.list_page(db)
        return CostRestoreDefaultsVO(
            location=None if latest is None else latest.location,
            year=None if latest is None else latest.year,
            month=None if latest is None else latest.month,
            vehicle_model=None if latest is None else latest.vehicle_model,
            locations=self._locations.list_enabled(db),
            vehicle_models=[
                CostRestoreVehicleChoiceVO(
                    location=item.location,
                    vehicle_model=item.vehicle_model,
                )
                for item in catalog.items
            ],
            suppliers=self._suppliers.list_registered_names(db),
        )

    def query_page(
        self,
        db: Session,
        query: CostRestoreProcurementObjectQuery,
    ) -> tuple[list[CostRestoreLineVO], int, CostRestoreScopeVO]:
        hits, scope = self._select_hits(db, query)
        page_hits = slice_objects(hits, query.page, query.size)
        lines = self._lines_for(db, query, page_hits)
        return [line_to_vo(line) for line in lines], len(hits), scope

    def lines_for_export(
        self,
        db: Session,
        query: CostRestoreProcurementObjectQuery,
    ) -> tuple[list[RestoreLine], CostRestoreScopeVO]:
        hits, scope = self._select_hits(db, query)
        return self._lines_for(db, query, hits), scope

    def _select_hits(
        self,
        db: Session,
        query: CostRestoreProcurementObjectQuery,
    ) -> tuple[list[ObjectHit], CostRestoreScopeVO]:
        headers = self._lists.list_lists_by_location(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
        )
        if not headers:
            raise BusinessException(_NO_LIST)
        nodes_by_id = self._nodes_for(db, headers)
        hits: list[ObjectHit] = []
        for header in headers:
            for obj in self._lists.list_objects_by_list_id(db, header.id):
                if obj.section != SECTION_OBJECT:
                    continue
                if query.supplier_name and obj.supplier_name != query.supplier_name:
                    continue
                node = nodes_by_id.get(obj.source_node_id)
                if node is None:
                    continue
                l0 = l0_node_of(node.id, nodes_by_id)
                if l0 is None or not is_in_period(
                    effective_year=l0.effective_year,
                    effective_month=l0.effective_month,
                    expiry_year=l0.expiry_year,
                    expiry_month=l0.expiry_month,
                    as_of_year=query.year,
                    as_of_month=query.month,
                ):
                    continue
                hits.append(
                    ObjectHit(
                        object_id=obj.id,
                        supplier_name=obj.supplier_name,
                        vehicle_model=header.vehicle_model,
                        object_kind_label=KIND_LABELS.get(
                            obj.object_kind or "", obj.object_kind or ""
                        ),
                        internal_number=obj.internal_number,
                        part_number=obj.part_number,
                        part_name=obj.part_name,
                        vehicle_qty=vehicle_qty_from_l0(node.id, nodes_by_id),
                        level=obj.level,
                        source_node_id=obj.source_node_id,
                        excel_filename=obj.excel_filename or "",
                        excel_sheet_name=obj.excel_sheet_name or "",
                        excel_row=obj.excel_row or 0,
                    )
                )
        hits.sort(
            key=lambda hit: (
                hit.vehicle_model,
                hit.excel_filename,
                hit.excel_sheet_name,
                hit.excel_row,
                hit.object_id,
            )
        )
        qa_passed = all(header.qa_passed for header in headers)
        scope = CostRestoreScopeVO(
            location=query.location,
            year=query.year,
            month=query.month,
            vehicle_model=query.vehicle_model,
            scope_label=query.vehicle_model or "全部项目",
            qa_passed=qa_passed,
            qa_note=None if qa_passed else "检测未通过",
        )
        return hits, scope

    def _nodes_for(
        self, db: Session, headers: list[BomProcurementObjectList]
    ) -> dict[int, BomNode]:
        nodes_by_id: dict[int, BomNode] = {}
        for snapshot_id in dict.fromkeys(header.snapshot_id for header in headers):
            for node in self._nodes.list_by_snapshot(db, snapshot_id):
                nodes_by_id[node.id] = node
        return nodes_by_id

    def _lines_for(
        self,
        db: Session,
        query: CostRestoreProcurementObjectQuery,
        hits: list[ObjectHit],
    ) -> list[RestoreLine]:
        if not hits:
            return []
        cards = self._cards.list_with_items_by_source_nodes(
            db,
            year=query.year,
            month=query.month,
            location=query.location,
            source_node_ids=[hit.source_node_id for hit in hits],
        )
        card_by_key = {(card.vehicle_model, card.source_node_id): card for card in cards}
        chosen = [card_by_key.get((hit.vehicle_model, hit.source_node_id)) for hit in hits]
        present = [card for card in chosen if card is not None]
        bundle = self._load_bundle(db, query, hits, present)
        lines: list[RestoreLine] = []
        for hit, card in zip(hits, chosen, strict=True):
            lines.extend(build_object_lines(hit, card, bundle))
        return lines

    def _load_bundle(
        self,
        db: Session,
        query: CostRestoreProcurementObjectQuery,
        hits: list[ObjectHit],
        cards: list[AssemblyCost],
    ) -> RestoreBundle:
        card_by_key = {(card.vehicle_model, card.source_node_id): card for card in cards}
        part_numbers: dict[str, list[str]] = defaultdict(list)
        for hit in hits:
            card = card_by_key.get((hit.vehicle_model, hit.source_node_id))
            if card is None:
                continue
            for item in card.items or []:
                if item.cost_source != "stamping":
                    continue
                part_numbers[hit.vehicle_model].append(
                    priced_part_number(item.part_number, item.match_hint)
                )
        part_costs: dict[tuple[str, str], list[StampingPartCost]] = defaultdict(list)
        for vehicle_model, numbers in part_numbers.items():
            for cost in self._part_costs.list_success_by_part_numbers(
                db,
                year=query.year,
                month=query.month,
                location=query.location,
                vehicle_model=vehicle_model,
                part_numbers=numbers,
            ):
                part_costs[(vehicle_model, cost.part_number)].append(cost)
        process_ids = [
            cost.process_fee_id
            for rows in part_costs.values()
            for cost in rows
            if cost.process_fee_id
        ]
        die_ids = [
            cost.die_fee_id for rows in part_costs.values() for cost in rows if cost.die_fee_id
        ]
        process_fees = {fee.id: fee for fee in self._process_fees.list_by_ids(db, process_ids)}
        die_fees = {fee.id: fee for fee in self._die_fees.list_by_ids(db, die_ids)}
        die_process_ids = [
            item.source_die_process_id
            for fee in die_fees.values()
            for item in (fee.items or [])
            if item.source_die_process_id
        ]
        die_processes = {
            row.id: row for row in self._die_processes.list_by_ids(db, die_process_ids)
        }
        weld_ids = [card.welding_fee_id for card in cards if card.welding_fee_id]
        welding_fees = {fee.id: fee for fee in self._welding.list_by_ids(db, weld_ids)}
        part_ids = [cost.source_part_id for rows in part_costs.values() for cost in rows]
        blanks: dict[int, list[StampingTailorWeldBlank]] = defaultdict(list)
        for blank in self._blanks.list_by_part_ids(db, part_ids):
            blanks[blank.part_id].append(blank)
        return RestoreBundle(
            part_costs=dict(part_costs),
            process_fees=process_fees,
            die_fees=die_fees,
            die_processes=die_processes,
            welding_fees=welding_fees,
            blanks_by_part_id=dict(blanks),
        )
