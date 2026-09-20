"""L0 树期查询：算法在 period_trees，这里只取林再套口径。"""

from sqlalchemy.orm import Session

from app.models.bom import BomNode
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.period_trees import (
    is_tree_root,
    node_ids_for_l0_version,
    nodes_in_as_of_trees,
    nodes_in_year_overlap_trees,
    tree_root_of,
)


class BomPeriodRepository:
    """L0 树期：当月命中 / 年交集 / 树根版本字。"""

    def __init__(self) -> None:
        self._nodes = BomNodeRepository()

    def list_as_of_trees(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        as_of_year: int,
        as_of_month: int,
    ) -> list[BomNode]:
        """L0 命中 as_of 的树（含子树）。按月命中以树根为准。"""
        all_nodes = self._nodes.list_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )
        return nodes_in_as_of_trees(all_nodes, as_of_year=as_of_year, as_of_month=as_of_month)

    def list_year_overlap_trees(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        year: int,
    ) -> list[BomNode]:
        """该基地+项目：树根年交集命中的整棵树。"""
        all_nodes = self._nodes.list_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )
        return nodes_in_year_overlap_trees(all_nodes, year=year)

    def node_ids_overlapping_year(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        year: int,
    ) -> set[int]:
        return {
            int(node.id)
            for node in self.list_year_overlap_trees(
                db, location=location, vehicle_model=vehicle_model, year=year
            )
        }

    def node_ids_for_l0_version(
        self,
        db: Session,
        *,
        bom_version: str,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> set[int]:
        """树根版本字命中的子树节点 id。下游只按 source_node_id 收口。"""
        forest = self._list_forest(
            db, location=location, locations=locations, vehicle_model=vehicle_model
        )
        return node_ids_for_l0_version(forest, bom_version=bom_version)

    def map_tree_root_version_by_node_id(
        self,
        db: Session,
        node_ids: list[int],
    ) -> dict[int, str]:
        """任意节点 → 所属 L0 树根版本字。"""
        ids = sorted({int(node_id) for node_id in node_ids if node_id})
        if not ids:
            return {}
        seeds = db.query(BomNode).filter(BomNode.id.in_(ids)).all()
        snapshot_ids = {int(node.snapshot_id) for node in seeds if node.snapshot_id is not None}
        forest = (
            db.query(BomNode).filter(BomNode.snapshot_id.in_(snapshot_ids)).all()
            if snapshot_ids
            else []
        )
        by_id = {int(node.id): node for node in forest}
        result: dict[int, str] = {}
        for seed_id in ids:
            node = by_id.get(seed_id)
            if node is None:
                continue
            root = tree_root_of(node, by_id)
            version = (root.bom_version or "").strip()
            if version:
                result[seed_id] = version
        return result

    def list_l0_versions(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        year: int | None = None,
    ) -> list[str]:
        """基地+项目（可选年交集）下，树根版本字。下拉不从拆解/费行反推。"""
        forest = self._list_forest(
            db, location=location, locations=locations, vehicle_model=vehicle_model
        )
        nodes = nodes_in_year_overlap_trees(forest, year=year) if year is not None else forest
        versions = {
            (node.bom_version or "").strip()
            for node in nodes
            if is_tree_root(node) and (node.bom_version or "").strip()
        }
        return sorted(versions)

    def _list_forest(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> list[BomNode]:
        query = db.query(BomNode)
        if locations is not None:
            query = query.filter(BomNode.location.in_(locations))
        elif location:
            query = query.filter(BomNode.location == location)
        if vehicle_model:
            query = query.filter(BomNode.vehicle_model == vehicle_model)
        return query.all()
