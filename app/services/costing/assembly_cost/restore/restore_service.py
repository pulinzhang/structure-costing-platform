"""总成核价成本还原 — 只读装配，不算价。

对外入口：AssemblyCostRestoreService。卡片/树/恒等式为同目录独立类。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
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
from app.repositories.bom.bom.node import BomNodeRepository
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
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.repositories.stamping.gauge_fee.repository import StampingGaugeFeeRepository
from app.repositories.stamping.process_fee.repository import (
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
    RestoreDieOpVO,
    RestoreDocumentRefVO,
    RestoreExceptionVO,
    RestoreMaterialNodeVO,
    RestoreProcessOpVO,
    RestoreStampingVO,
    RestoreSteelVO,
)
from app.services.costing.assembly_cost.codes import card_short_code, is_purchased_assembly_root
from app.services.costing.assembly_cost.restore.documents import RestoreDocuments
from app.services.costing.assembly_cost.restore.identity import RestoreIdentity
from app.services.costing.assembly_cost.restore.labels import (
    HIGHLIGHT_ASSEMBLY_PRICE,
    HIGHLIGHT_SETTLEMENT_PRICE,
)
from app.services.costing.assembly_cost.restore.lookups import RestoreLookups
from app.services.costing.assembly_cost.restore.material import RestoreMaterial
from app.services.costing.assembly_cost.restore.money import _money
from app.services.costing.assembly_cost.restore.stamping import RestoreStamping
from app.services.costing.assembly_cost.restore.tree import RestoreTree
from app.services.costing.assembly_cost.restore.welding import RestoreWelding
from app.services.settings.system.service import SettingsService


class AssemblyCostRestoreService:
    """按核价卡还原「当时怎么算出来的」。不重算、不写库。"""

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
        self._tree = RestoreTree(self.node_repo)
        self._lookups = RestoreLookups(self.stamping_repo, self.annual_repo)
        self._documents = RestoreDocuments(self.upload_file_repo)
        self._stamping = RestoreStamping(self._documents)
        self._material = RestoreMaterial(self._tree, self._stamping)
        self._welding = RestoreWelding(self.welding_repo)
        self._identity = RestoreIdentity()

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
        """装配顺序：卡 → 快照树 → 冲压/年价 → 织树 → 焊接/摊入 → 恒等式 → 文件。"""
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
        tree_from_snapshot, parent_by_id, snapshot_nodes = self._tree._snapshot_parents(
            db, card, exceptions
        )
        stamping_by_part = self._lookups._load_stamping(db, card, items)
        annual_by_part = self._lookups._load_annual(db, card, items)
        process_by_id, die_by_id, gauge_ids = self._lookups._collect_fee_ids(stamping_by_part)
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
                self._material._build_material_node(
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
            material_nodes = self._tree._weave_sub_assemblies(
                card=card,
                item_nodes=material_nodes,
                snapshot_nodes=snapshot_nodes,
                parent_by_id=parent_by_id,
                view=report_view,
            )

        welding = self._welding._build_welding(db, card, exceptions)
        rows = self.packaging_repo.list_by_location_year(db, location=card.location, year=card.year)
        packaging = next((row for row in rows if row.part_number == card.part_number), None)
        indirects = self._welding._build_indirects(card, packaging, exceptions)
        if packaging is not None and packaging.excel_filename:
            self._documents._add_document(
                documents,
                file_category="bom_packaging_transport_fee",
                filename=packaging.excel_filename,
                excel_row=packaging.excel_row,
                short_code=short,
            )

        identity = self._identity._identity_checks(card, items, exceptions)
        highlight_amount = card.total_amount if report_view == "procurement" else card.grand_total
        highlight_label = (
            HIGHLIGHT_SETTLEMENT_PRICE if report_view == "procurement" else HIGHLIGHT_ASSEMBLY_PRICE
        )
        purchased_assembly = is_purchased_assembly_root(card.source_node_id, items)

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
            documents=self._documents._merge_documents(documents),
            company_name=self.settings_service.get_config(db).company_name or "",
            calculated_by=(
                (
                    getattr(card, "updated_by", None) or getattr(card, "created_by", None) or ""
                ).strip()
            ),
            is_purchased_assembly=purchased_assembly,
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
        return self._stamping._build_steel(
            picked, steel_map, base_price_map, exceptions, short, part_number
        )

    def _process_ops(self, process_row: StampingProcessFee | None) -> list[RestoreProcessOpVO]:
        return self._stamping._process_ops(process_row)

    def _die_ops(self, die_row: StampingDieFee | None) -> list[RestoreDieOpVO]:
        return self._stamping._die_ops(die_row)

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
        return self._stamping._build_stamping(
            db=db,
            item=item,
            short=short,
            rows=rows,
            process_map=process_map,
            die_map=die_map,
            gauge_map=gauge_map,
            steel_map=steel_map,
            base_price_map=base_price_map,
            scrap_map=scrap_map,
            exceptions=exceptions,
            documents=documents,
        )
