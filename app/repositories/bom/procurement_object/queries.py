"""采购对象清单查询：清单/对象、分页、导出、HUD、生成日志。"""

from sqlalchemy import and_, func
from sqlalchemy.orm import Query, Session, aliased

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom.node import BomNode
from app.models.bom.procurement_object import (
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import BomProcurementObjectGenerateLog
from app.repositories.bom.procurement_object.types import (
    KIND_L0_DEGENERATE,
    SECTION_OBJECT,
    ProcurementObjectAuditSummary,
    ProcurementObjectScopeFilters,
    count_matching,
)
from app.repositories.period_query import period_hit_clause

L0Period = tuple[int, int, int | None, int | None]


class BomProcurementObjectQueries:
    def get_list_by_id(self, db: Session, list_id: int) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .filter(BomProcurementObjectList.id == list_id)
            .first()
        )

    def get_list_by_snapshot_id(
        self, db: Session, snapshot_id: int
    ) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .filter(BomProcurementObjectList.snapshot_id == snapshot_id)
            .first()
        )

    def has_list_for_location(self, db: Session, location: str) -> bool:
        return (
            db.query(BomProcurementObjectList.id)
            .filter(BomProcurementObjectList.location == location)
            .first()
            is not None
        )

    def get_list_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomProcurementObjectList | None:
        """按清单头三键找头（头上 SOP 字，与 snapshot 头同形）。

        现网调用方：BOM 覆盖/删除门禁、总成 seq_label 等「已知 SOP 头键」场景。
        **生成 / 供应商批传** 走 `get_list_by_snapshot_id`（经 `snapshot_scope`）。
        列表 / 批量 / 导出 / 协议 **禁止**用本方法取件
        （须 `list_lists_by_location_vehicle`；版本浏览裁爬到的 L0）。
        """
        return (
            db.query(BomProcurementObjectList)
            .filter(
                BomProcurementObjectList.location == location,
                BomProcurementObjectList.vehicle_model == vehicle_model,
                BomProcurementObjectList.bom_version == bom_version,
            )
            .first()
        )

    def list_lists_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomProcurementObjectList]:
        return (
            db.query(BomProcurementObjectList)
            .filter(
                BomProcurementObjectList.location == location,
                BomProcurementObjectList.vehicle_model == vehicle_model,
            )
            .order_by(BomProcurementObjectList.id.asc())
            .all()
        )

    def list_objects_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomProcurementObject]:
        objects: list[BomProcurementObject] = []
        for header in self.list_lists_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        ):
            objects.extend(self.list_objects_by_list_id(db, header.id))
        return objects

    def get_latest_list(self, db: Session) -> BomProcurementObjectList | None:
        return (
            db.query(BomProcurementObjectList)
            .order_by(
                BomProcurementObjectList.generated_at.desc(),
                BomProcurementObjectList.id.desc(),
            )
            .first()
        )

    def get_object_by_id(self, db: Session, object_id: int) -> BomProcurementObject | None:
        return db.query(BomProcurementObject).filter(BomProcurementObject.id == object_id).first()

    def get_confirm_status_by_id(self, db: Session, object_id: int) -> str | None:
        obj = self.get_object_by_id(db, object_id)
        if obj is None:
            return None
        return obj.confirm_status

    def map_confirm_status_by_ids(self, db: Session, object_ids: list[int]) -> dict[int, str]:
        unique_ids = [item for item in object_ids if item is not None]
        if not unique_ids:
            return {}
        rows = (
            db.query(BomProcurementObject.id, BomProcurementObject.confirm_status)
            .filter(BomProcurementObject.id.in_(unique_ids))
            .all()
        )
        return {int(row_id): status for row_id, status in rows}

    def list_objects_by_list_id(self, db: Session, list_id: int) -> list[BomProcurementObject]:
        return (
            db.query(BomProcurementObject)
            .filter(BomProcurementObject.list_id == list_id)
            .order_by(BomProcurementObject.section, BomProcurementObject.id)
            .all()
        )

    def count_approved_objects(self, db: Session, list_id: int) -> int:
        return (
            db.query(BomProcurementObject)
            .filter(
                BomProcurementObject.list_id == list_id,
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_APPROVED,
            )
            .count()
        )

    def paginate_objects(
        self,
        db: Session,
        *,
        scope: ProcurementObjectScopeFilters,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObject], int]:
        query = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            scope,
        )
        total = query.count()
        rows = self._apply_check_order(query).offset(skip).limit(limit).all()
        return rows, total

    def list_objects_for_export(
        self,
        db: Session,
        *,
        scope: ProcurementObjectScopeFilters,
    ) -> list[BomProcurementObject]:
        query = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            scope,
        )
        return self._apply_check_order(query).all()

    def summarize_objects(
        self,
        db: Session,
        *,
        scope: ProcurementObjectScopeFilters,
    ) -> ProcurementObjectAuditSummary:
        base = self._apply_object_filters(
            db.query(BomProcurementObject).join(BomProcurementObjectList),
            scope,
        )
        row = base.with_entities(
            func.count(BomProcurementObject.id).label("total_count"),
            count_matching(
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_PENDING,
            ).label("pending_count"),
            count_matching(
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.audit_status == AUDIT_APPROVED,
            ).label("approved_count"),
            count_matching(BomProcurementObject.section == SECTION_OBJECT).label("object_count"),
            count_matching(
                BomProcurementObject.section == SECTION_OBJECT,
                BomProcurementObject.object_kind == KIND_L0_DEGENERATE,
            ).label("object_l0_degenerate_count"),
            count_matching(BomProcurementObject.section == "other_leaf").label("other_leaf_count"),
            count_matching(BomProcurementObject.section == "anomaly").label("anomaly_count"),
        ).one()
        return {
            "total_count": int(row.total_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "object_count": int(row.object_count or 0),
            "object_l0_degenerate_count": int(row.object_l0_degenerate_count or 0),
            "other_leaf_count": int(row.other_leaf_count or 0),
            "anomaly_count": int(row.anomaly_count or 0),
        }

    def _apply_object_filters(
        self,
        query: Query[BomProcurementObject],
        scope: ProcurementObjectScopeFilters,
    ) -> Query[BomProcurementObject]:
        location = scope["location"]
        locations = scope["locations"]
        vehicle_model = scope["vehicle_model"]
        bom_version = scope["bom_version"]
        section = scope["section"]
        object_kind = scope["object_kind"]
        confirm_status = scope["confirm_status"]
        audit_status = scope["audit_status"]
        part_number = scope["part_number"]
        l0_part_number = scope["l0_part_number"]
        excel_row = scope["excel_row"]
        supplier_names = scope["supplier_names"]
        has_supplier = scope["has_supplier"]
        as_of_year = scope["as_of_year"]
        as_of_month = scope["as_of_month"]
        if locations is not None:
            query = query.filter(BomProcurementObjectList.location.in_(locations))
        elif location:
            query = query.filter(BomProcurementObjectList.location == location)
        if vehicle_model:
            query = query.filter(BomProcurementObjectList.vehicle_model == vehicle_model)
        if section:
            query = query.filter(BomProcurementObject.section == section)
        if object_kind:
            query = query.filter(BomProcurementObject.object_kind == object_kind)
        if confirm_status:
            query = query.filter(BomProcurementObject.confirm_status == confirm_status)
        if audit_status:
            query = query.filter(BomProcurementObject.audit_status == audit_status)
        if part_number:
            query = query.filter(BomProcurementObject.part_number.like(f"%{part_number}%"))
        if l0_part_number:
            query = query.filter(BomProcurementObject.l0_part_number.like(f"%{l0_part_number}%"))
        if excel_row is not None:
            query = query.filter(BomProcurementObject.excel_row == excel_row)
        if supplier_names is not None:
            query = query.filter(BomProcurementObject.supplier_name.in_(supplier_names))
        if has_supplier is True:
            query = query.filter(BomProcurementObject.supplier_name.isnot(None))
        elif has_supplier is False:
            query = query.filter(BomProcurementObject.supplier_name.is_(None))
        if (as_of_year is not None and as_of_month is not None) or bom_version:
            # 有效期 / 版本浏览只认所属 L0 树根（与 map_l0_periods 同钥：
            # snapshot_id + l0_part_number + level=0 ≡ 爬到树根；禁止 source 本行 / 清单头字）。
            tree_root = aliased(BomNode)
            query = query.join(
                tree_root,
                and_(
                    tree_root.snapshot_id == BomProcurementObjectList.snapshot_id,
                    tree_root.part_number == BomProcurementObject.l0_part_number,
                    tree_root.level == 0,
                ),
            )
            if as_of_year is not None and as_of_month is not None:
                query = query.filter(
                    period_hit_clause(
                        tree_root.effective_year,
                        tree_root.effective_month,
                        tree_root.expiry_year,
                        tree_root.expiry_month,
                        as_of_year,
                        as_of_month,
                    )
                )
            if bom_version:
                query = query.filter(tree_root.bom_version == bom_version)
        return query

    def map_l0_periods(
        self,
        db: Session,
        *,
        snapshot_l0_keys: list[tuple[int, str]],
    ) -> dict[tuple[int, str], L0Period]:
        """(snapshot_id, l0_part_number) → 所属树根四列。"""
        if not snapshot_l0_keys:
            return {}
        wanted = set(snapshot_l0_keys)
        snapshot_ids = {snapshot_id for snapshot_id, _ in wanted}
        part_numbers = {part_number for _, part_number in wanted}
        rows = (
            db.query(
                BomNode.snapshot_id,
                BomNode.part_number,
                BomNode.effective_year,
                BomNode.effective_month,
                BomNode.expiry_year,
                BomNode.expiry_month,
            )
            .filter(
                BomNode.snapshot_id.in_(snapshot_ids),
                BomNode.part_number.in_(part_numbers),
                BomNode.level == 0,
            )
            .all()
        )
        result: dict[tuple[int, str], L0Period] = {}
        for snapshot_id, part_number, ey, em, xy, xm in rows:
            key = (int(snapshot_id), str(part_number))
            if key in wanted:
                result[key] = (int(ey), int(em), xy, xm)
        return result

    @staticmethod
    def _apply_check_order(
        query: Query[BomProcurementObject],
    ) -> Query[BomProcurementObject]:
        """核对顺序：基地 → 车型 → BOM版本 → 原始文件名 → 工作表 → Excel行号。"""
        original_filename = func.coalesce(
            BomProcurementObject.excel_filename,
            BomProcurementObjectList.source_filename,
        )
        return query.order_by(
            BomProcurementObjectList.location,
            BomProcurementObjectList.vehicle_model,
            BomProcurementObjectList.bom_version,
            original_filename,
            BomProcurementObject.excel_sheet_name,
            BomProcurementObject.excel_row,
            BomProcurementObject.id,
        )

    def get_generate_log_by_id(
        self, db: Session, log_id: int
    ) -> BomProcurementObjectGenerateLog | None:
        return (
            db.query(BomProcurementObjectGenerateLog)
            .filter(BomProcurementObjectGenerateLog.id == log_id)
            .first()
        )

    def paginate_generate_logs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObjectGenerateLog], int]:
        query = db.query(BomProcurementObjectGenerateLog)
        if location:
            query = query.filter(BomProcurementObjectGenerateLog.location == location)
        if vehicle_model:
            query = query.filter(BomProcurementObjectGenerateLog.vehicle_model == vehicle_model)
        if bom_version:
            query = query.filter(BomProcurementObjectGenerateLog.bom_version == bom_version)
        total = query.count()
        records = (
            query.order_by(BomProcurementObjectGenerateLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total
