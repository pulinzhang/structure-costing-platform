"""零件用在哪：命中、向上追父、连乘用量。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.bom.manufacturing_category import short_part_number_digits
from app.common.part_number import part_number_like_pattern
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.repositories.bom.bom.node import BomNodeRepository
from app.schemas.dto.bom_where_used_dto import BomWhereUsedQuery
from app.schemas.vo.bom_where_used_vo import (
    BomWhereUsedNodeVO,
    BomWhereUsedPathVO,
    BomWhereUsedSummaryVO,
    BomWhereUsedVO,
)
from app.services.bom.where_used.match import HIT_LIMIT, SHORT_CODE_CANDIDATE_LIMIT, plan_match
from app.services.masterdata.location.location_service import LocationService

_ONE = Decimal("1")
_PARENT_WALK_LIMIT = 8


class BomWhereUsedService:
    """只读反查。"""

    def __init__(self) -> None:
        self._node_repo = BomNodeRepository()
        self._location_service = LocationService()

    def search(self, db: Session, query: BomWhereUsedQuery) -> BomWhereUsedVO:
        kind, token, name_raw = plan_match(raw_query=query.query, match=query.match)
        locations: list[str] | None = None
        if query.location:
            locations = self._location_service.expand_for_query(db, query.location)
            if not locations:
                return self._empty()
        statuses = None if query.status == "all" else [query.status]
        hits = self._load_hits(
            db,
            kind=kind,
            token=token,
            name_raw=name_raw,
            locations=locations,
            vehicle_model=query.vehicle_model or None,
            bom_version=query.bom_version or None,
            statuses=statuses,
        )
        if len(hits) > HIT_LIMIT:
            raise BusinessException(
                "命中节点过多，请加上基地、项目或版本，或把名称写长一点",
                code=409,
            )
        if not hits:
            return self._empty()
        by_id = self._load_ancestors(db, hits)
        paths = [self._build_path(hit, by_id, depth=query.depth) for hit in hits]
        snapshot_ids = {path.snapshot_id for path in paths}
        vehicle_models = {path.vehicle_model for path in paths}
        return BomWhereUsedVO(
            summary=BomWhereUsedSummaryVO(
                hit_count=len(hits),
                snapshot_count=len(snapshot_ids),
                vehicle_model_count=len(vehicle_models),
            ),
            paths=paths,
        )

    def _load_hits(
        self,
        db: Session,
        *,
        kind: str,
        token: str,
        name_raw: str,
        locations: list[str] | None,
        vehicle_model: str | None,
        bom_version: str | None,
        statuses: list[str] | None,
    ) -> list[BomNode]:
        if kind == "internal_number":
            return self._node_repo.list_where_used_hits(
                db,
                locations=locations,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                statuses=statuses,
                part_number_like=None,
                part_name_like=None,
                internal_number=token,
                fetch_limit=HIT_LIMIT + 1,
            )
        if kind == "short_code":
            candidates = self._node_repo.list_where_used_hits(
                db,
                locations=locations,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                statuses=statuses,
                part_number_like=part_number_like_pattern(token),
                part_name_like=None,
                internal_number=None,
                fetch_limit=SHORT_CODE_CANDIDATE_LIMIT,
            )
            return [row for row in candidates if short_part_number_digits(row.part_number) == token]
        return self._node_repo.list_where_used_hits(
            db,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=statuses,
            part_number_like=part_number_like_pattern(token),
            part_name_like=part_number_like_pattern(name_raw),
            internal_number=None,
            fetch_limit=HIT_LIMIT + 1,
        )

    def _load_ancestors(self, db: Session, hits: list[BomNode]) -> dict[int, BomNode]:
        by_id: dict[int, BomNode] = {row.id: row for row in hits}
        frontier = [row.parent_id for row in hits if row.parent_id and row.parent_id not in by_id]
        for _ in range(_PARENT_WALK_LIMIT):
            if not frontier:
                break
            loaded = self._node_repo.list_by_ids(db, frontier)
            for row in loaded:
                by_id[row.id] = row
            frontier = [
                row.parent_id for row in loaded if row.parent_id and row.parent_id not in by_id
            ]
        return by_id

    def _build_path(
        self,
        hit: BomNode,
        by_id: dict[int, BomNode],
        *,
        depth: str,
    ) -> BomWhereUsedPathVO:
        chain = self._walk_to_root(hit, by_id)
        l0 = chain[-1]
        snapshot = hit.snapshot
        display_nodes = chain if depth == "multi" else chain[:2]
        path_qty = _ONE
        for node in chain:
            path_qty *= node.qty if node.qty is not None else _ONE
        return BomWhereUsedPathVO(
            snapshot_id=hit.snapshot_id,
            location=snapshot.location,
            vehicle_model=snapshot.vehicle_model,
            bom_version=snapshot.bom_version,
            nodes=[self._to_node_vo(node) for node in display_nodes],
            path_qty=path_qty,
            l0_node_id=l0.id,
            l0_part_number=l0.part_number,
        )

    def _walk_to_root(self, hit: BomNode, by_id: dict[int, BomNode]) -> list[BomNode]:
        chain: list[BomNode] = []
        seen: set[int] = set()
        current: BomNode | None = hit
        for _ in range(_PARENT_WALK_LIMIT):
            if current is None:
                break
            if current.id in seen:
                break
            seen.add(current.id)
            chain.append(current)
            if current.parent_id is None:
                break
            current = by_id.get(current.parent_id)
        return chain

    @staticmethod
    def _to_node_vo(node: BomNode) -> BomWhereUsedNodeVO:
        return BomWhereUsedNodeVO(
            node_id=node.id,
            level=int(node.level),
            part_number=node.part_number,
            part_name=node.part_name,
            internal_number=node.internal_number,
            qty=node.qty,
            qty_text=node.qty_text,
            sketch_url=node.sketch_url,
            material=node.material,
            thickness_text=node.thickness_text,
            material_mill=node.material_mill,
            part_weight=node.part_weight,
            weld_info=node.weld_info,
            remark=node.remark,
            excel_filename=node.excel_filename,
            excel_sheet_name=node.excel_sheet_name,
            excel_row=node.excel_row,
        )

    @staticmethod
    def _empty() -> BomWhereUsedVO:
        return BomWhereUsedVO(
            summary=BomWhereUsedSummaryVO(
                hit_count=0,
                snapshot_count=0,
                vehicle_model_count=0,
            ),
            paths=[],
        )
