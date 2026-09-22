"""BOM 清单头：列表、创建、删除、级联筛、下游占用。"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.bom.bom.types import BomSnapshotListFilters
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_dto import (
    BomCascadeFilterQuery,
    BomSnapshotCreate,
    BomSnapshotQuery,
    BomSnapshotWrite,
)
from app.schemas.vo.bom_vo import BomCascadeFilterOptionsVO, BomSnapshotVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.delete_block import explain_bom_delete_blocked
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService

logger = logging.getLogger("service.bom.snapshot")

_ALLOWED_STAGES = {"initial", "mass"}
_ALLOWED_STATUSES = {"draft", "active", "archived"}


class BomSnapshotService:
    """材料清单版本。"""

    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self._procurement_repo = BomProcurementObjectRepository()
        self._breakdown_repo = BomWeldingProcessBreakdownRepository()

    def assert_bom_scope_unused(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        action: str,
    ) -> None:
        """有直接下游（采购对象、焊接拆解）则禁止覆盖导入或删除材料清单/节点。

        此处 bom_version = snapshot 头 SOP 字，与清单头冗余键同形；不是列表浏览的 L0 字。
        """
        found: list[str] = []
        if self._procurement_repo.get_list_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        ):
            found.append("采购对象清单")
        snapshot = self.snapshot_repo.get_by_unique_key(db, location, vehicle_model, bom_version)
        if snapshot is not None and self._breakdown_repo.exists_by_snapshot_id(db, snapshot.id):
            found.append("焊接工艺拆解")
        if not found:
            return
        guides: list[str] = []
        if "采购对象清单" in found:
            guides.append("请打开「焊接工程 → 采购对象 → 采购对象清单」，删掉这一版清单。")
        if "焊接工艺拆解" in found:
            guides.append("请打开「焊接工程 → 焊接工艺拆解 → 拆解列表」，删掉这一版拆解。")
        raise BusinessException(
            f"这一版材料清单还不能{action}。" + "".join(guides),
            code=409,
        )

    def paginate_snapshots(
        self, db: Session, query: BomSnapshotQuery
    ) -> tuple[list[BomSnapshotVO], int, BomSnapshotListFilters]:
        skip = (query.page - 1) * query.size
        location_service = LocationService()
        locations: list[str] | None = None
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                empty_filters: BomSnapshotListFilters = {
                    "locations": location_service.list_registered(db),
                    "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
                    "bom_versions": self.snapshot_repo.list_bom_versions(db),
                    "statuses": self.snapshot_repo.list_statuses(db),
                    "summary": {
                        "total_count": 0,
                        "active_count": 0,
                        "draft_count": 0,
                        "archived_count": 0,
                        "total_node_count": 0,
                    },
                }
                return [], 0, empty_filters
        rows, total = self.snapshot_repo.paginate(
            db,
            locations=locations,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            status=query.status,
            skip=skip,
            limit=query.size,
        )
        items: list[BomSnapshotVO] = []
        for row in rows:
            vo = BomSnapshotVO.model_validate(row)
            vo.node_count = self.snapshot_repo.count_nodes(db, row.id)
            items.append(vo)

        summary_raw = self.snapshot_repo.summarize(
            db,
            locations=locations,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            status=query.status,
        )
        filters: BomSnapshotListFilters = {
            "locations": location_service.list_registered(db),
            "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
            "bom_versions": self.snapshot_repo.list_bom_versions(db),
            "statuses": self.snapshot_repo.list_statuses(db),
            "summary": summary_raw,
        }
        return items, total, filters

    def get_cascade_filter_options(
        self,
        db: Session,
        query: BomCascadeFilterQuery,
    ) -> BomCascadeFilterOptionsVO:
        location_service = LocationService()
        location_raw = (query.location or "").strip() or None
        locations: list[str] | None = None
        if location_raw:
            locations = location_service.expand_for_query(db, location_raw)
            if not locations:
                return BomCascadeFilterOptionsVO(
                    locations=location_service.list_enabled(db),
                    vehicle_models=[],
                    bom_versions=[],
                )
        as_of = query.year is not None and query.month is not None
        raw = self.snapshot_repo.get_cascade_filter_options(
            db,
            locations=locations,
            vehicle_model=query.vehicle_model,
            status=query.status,
            as_of_year=query.year if as_of else None,
            as_of_month=query.month if as_of else None,
            version_source=query.version_source,
        )
        vehicle_svc = VehicleModelService()
        if location_raw and query.year is not None:
            if query.month is not None:
                vehicle_models = vehicle_svc.list_introducible(
                    db, location_raw, query.year, query.month
                )
            else:
                vehicle_models = vehicle_svc.list_overlaps_year(db, location_raw, query.year)
        else:
            vehicle_models = vehicle_svc.list_filter_codes(db, location_raw)
        return BomCascadeFilterOptionsVO(
            locations=location_service.list_enabled(db),
            vehicle_models=vehicle_models,
            bom_versions=list(raw["bom_versions"]),
        )

    def get_snapshot(self, db: Session, snapshot_id: int) -> BomSnapshotVO:
        row = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not row:
            raise NotFoundException("BOM 清单不存在")
        vo = BomSnapshotVO.model_validate(row)
        vo.node_count = self.snapshot_repo.count_nodes(db, row.id)
        return vo

    def create_snapshot(
        self,
        db: Session,
        data: BomSnapshotCreate,
        current_user: UserVO,
    ) -> BomSnapshotVO:
        if data.stage not in _ALLOWED_STAGES:
            raise BusinessException(f"stage 无效，允许: {', '.join(sorted(_ALLOWED_STAGES))}")
        if data.status not in _ALLOWED_STATUSES:
            raise BusinessException(f"status 无效，允许: {', '.join(sorted(_ALLOWED_STATUSES))}")

        location = LocationService().require_enabled(db, data.location)
        existing = self.snapshot_repo.get_by_unique_key(
            db, location, data.vehicle_model, data.bom_version
        )
        if existing:
            raise BusinessException(
                f"BOM 已存在: {location} / {data.vehicle_model} / {data.bom_version}"
            )

        try:
            audit = audit_create(current_user)
            row = self.snapshot_repo.create(
                db,
                BomSnapshotWrite(
                    location=location,
                    vehicle_model=data.vehicle_model,
                    bom_version=data.bom_version,
                    source_filename=data.source_filename,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                    product_category=data.product_category,
                    customer_name=data.customer_name,
                    stage=data.stage,
                    doc_no=data.doc_no,
                    prepare_dept=data.prepare_dept,
                    doc_date=data.doc_date,
                    revision_date=data.revision_date,
                    title=data.title,
                    source_file_hash=data.source_file_hash,
                    status=data.status,
                    remark=data.remark,
                ),
            )
            db.commit()
            db.refresh(row)
            vo = BomSnapshotVO.model_validate(row)
            vo.node_count = 0
            return vo
        except IntegrityError:
            db.rollback()
            raise BusinessException("BOM 唯一键冲突（基地+车型+版本）") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建 BOM snapshot 失败")
            raise

    def delete_snapshot(self, db: Session, snapshot_id: int) -> None:
        row = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not row:
            raise NotFoundException("BOM 清单不存在")
        self.assert_bom_scope_unused(
            db,
            location=row.location,
            vehicle_model=row.vehicle_model,
            bom_version=row.bom_version,
            action="删除",
        )
        node_ids = [node.id for node in BomNodeRepository().list_by_snapshot(db, row.id)]
        location = row.location
        vehicle_model = row.vehicle_model
        try:
            self.snapshot_repo.delete(db, row)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                explain_bom_delete_blocked(
                    db,
                    node_ids,
                    location=location,
                    vehicle_model=vehicle_model,
                ),
                code=409,
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除 BOM snapshot 失败")
            raise
