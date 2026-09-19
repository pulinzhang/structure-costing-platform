"""采购对象行 Write 装配 — generate / 工程变更插行共用。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_PENDING
from app.schemas.dto.bom_procurement_object_dto import BomProcurementObjectWrite
from app.services.bom.procurement_object.classify import SECTION_OBJECT, ClassifiedRow
from app.services.masterdata.supplier import SupplierService

ConfirmTuple = tuple[str, str | None, datetime | None, str | None, str | None]
# source_node_id → ConfirmTuple
ConfirmByNode = dict[int, ConfirmTuple]


def build_object_row_write(
    db: Session,
    row: ClassifiedRow,
    *,
    list_id: int,
    confirm_by_node: ConfirmByNode,
    created_by: str | None,
    updated_by: str | None,
) -> BomProcurementObjectWrite:
    """
    分类行 → 落库 Write。
    始终 audit_status=pending（工程变更抄确认也不抄审核）。
    """
    confirm_status = "pending"
    confirmed_by = None
    confirmed_at = None
    confirm_remark = None
    supplier_name = None
    if row.section == SECTION_OBJECT and row.source_node_id in confirm_by_node:
        (
            confirm_status,
            confirmed_by,
            confirmed_at,
            confirm_remark,
            supplier_name,
        ) = confirm_by_node[row.source_node_id]
    if confirm_status == "in_house" or (
        supplier_name and not SupplierService().is_registered(db, supplier_name)
    ):
        supplier_name = None
    return BomProcurementObjectWrite(
        list_id=list_id,
        section=row.section,
        object_kind=row.object_kind,
        degenerate_subtype=row.degenerate_subtype,
        source_node_id=row.source_node_id,
        part_number=row.part_number,
        part_name=row.part_name,
        internal_number=row.internal_number,
        level=row.level,
        node_role=row.node_role,
        qty=row.qty,
        qty_unit=row.qty_unit,
        l0_part_number=row.l0_part_number,
        l0_part_name=row.l0_part_name,
        parent_part_number=row.parent_part_number,
        parent_part_name=row.parent_part_name,
        excel_filename=row.excel_filename,
        excel_sheet_name=row.excel_sheet_name,
        excel_row=row.excel_row,
        child_count=row.child_count,
        weld_info=row.weld_info,
        remark=row.remark,
        has_outsource_remark=row.has_outsource_remark,
        material=row.material,
        thickness_text=row.thickness_text,
        material_mill=row.material_mill,
        data_gap=row.data_gap,
        alert_code=row.alert_code,
        confirm_status=confirm_status,
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
        confirm_remark=confirm_remark,
        supplier_name=supplier_name,
        audit_status=AUDIT_PENDING,
        created_by=created_by,
        updated_by=updated_by,
    )
