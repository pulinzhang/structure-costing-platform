"""下游树范围：只问 L0 树根，再收子树。"""

from sqlalchemy.orm import Session

from app.models.bom import BomNode
from app.repositories.bom.bom.period import BomPeriodRepository


class BomPeriodService:
    """对外树期门。算法在 period_trees，取林在 BomPeriodRepository。"""

    def __init__(self) -> None:
        self._period_repo = BomPeriodRepository()

    def list_as_of_trees(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        as_of_year: int,
        as_of_month: int,
    ) -> list[BomNode]:
        """下游只问这里：树根当月命中的整棵树。"""
        return self._period_repo.list_as_of_trees(
            db,
            location=location,
            vehicle_model=vehicle_model,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )

    def list_year_overlap_trees(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        year: int,
    ) -> list[BomNode]:
        """下游只问这里：树根年交集命中的整棵树。"""
        return self._period_repo.list_year_overlap_trees(
            db, location=location, vehicle_model=vehicle_model, year=year
        )

    def node_ids_overlapping_year(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        year: int,
    ) -> set[int]:
        return self._period_repo.node_ids_overlapping_year(
            db, location=location, vehicle_model=vehicle_model, year=year
        )

    def node_ids_for_l0_version(
        self,
        db: Session,
        *,
        bom_version: str | None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> set[int] | None:
        """树根版本字命中的子树 id。None = 不按版本收口；空 set = 该字下没有节点。"""
        wanted = (bom_version or "").strip()
        if not wanted:
            return None
        return self._period_repo.node_ids_for_l0_version(
            db,
            bom_version=wanted,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
        )

    def map_tree_root_version_by_node_id(
        self,
        db: Session,
        node_ids: list[int],
    ) -> dict[int, str]:
        return self._period_repo.map_tree_root_version_by_node_id(db, node_ids)

    def list_l0_versions(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        year: int | None = None,
    ) -> list[str]:
        """列表筛版本下拉：树根字，不是拆解/费行存的头字。"""
        return self._period_repo.list_l0_versions(
            db,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            year=year,
        )
