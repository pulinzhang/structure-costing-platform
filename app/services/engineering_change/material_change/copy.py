"""改图抄切点：新号另插行，不改工艺 material。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.engineering_change.material_change.order_repository import (
    MaterialChangeOrderInsert,
    MaterialChangeOrderRepository,
)
from app.services.settings.schema_comment.service import ensure_deletable
from app.services.stamping.part.service import StampingPartService

_order_repo = MaterialChangeOrderRepository()
_parts = StampingPartService()


def copy_cutovers(db: Session, from_part_id: int, to_part_id: int) -> None:
    """旧号上全部成功切点抄到新号，含已经是抄来的。同一旧行对同一新号只抄一次。"""
    _parts.get_by_id(db, from_part_id)
    new_part = _parts.get_by_id(db, to_part_id)
    already = {
        row.copied_from_order_id for row in _order_repo.list_copies_by_source_part(db, to_part_id)
    }
    for order in _order_repo.list_success_by_source_part(db, from_part_id):
        if order.id in already:
            continue
        _order_repo.create(
            db,
            MaterialChangeOrderInsert(
                upload_log_id=order.upload_log_id,
                upload_file_id=order.upload_file_id,
                change_version=order.change_version,
                excel_row=None,
                location=new_part.location,
                stamping_supplier=new_part.stamping_supplier,
                vehicle_model=new_part.vehicle_model,
                effective_year=order.effective_year,
                effective_month=order.effective_month,
                part_number=new_part.part_number,
                before_material=order.before_material,
                after_material=order.after_material,
                before_thickness=order.before_thickness,
                after_thickness=order.after_thickness,
                interchangeability=order.interchangeability,
                part_name=new_part.part_name or "",
                source_part_id=new_part.id,
                created_by=order.created_by,
                updated_by=order.updated_by,
                copied_from_order_id=order.id,
            ),
        )


def delete_copied_cutovers(db: Session, part_id: int) -> None:
    """只删该号上的抄行。原切点不动。"""
    for row in _order_repo.list_copies_by_source_part(db, part_id):
        ensure_deletable(
            db,
            "engineering_change_material_orders",
            [{"id": row.id}],
            subject="该材料变更单",
        )
        _order_repo.delete(db, row)
