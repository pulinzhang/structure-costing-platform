"""冲压零件抽屉：材料变更切点历史。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.period import previous_month
from app.repositories.engineering_change.material_change.order_repository import (
    MaterialChangeOrderRepository,
)
from app.repositories.engineering_change.material_change.upload_log_repository import (
    MaterialChangeUploadLogRepository,
)
from app.schemas.vo.engineering_change.material_change import MaterialChangeRecordVO
from app.services.stamping.part.service import StampingPartService

_order_repo = MaterialChangeOrderRepository()
_log_repo = MaterialChangeUploadLogRepository()


def list_part_records(db: Session, part_id: int) -> list[MaterialChangeRecordVO]:
    """这一号身份上的成功切点，按生效月升序。有效止是下一刀的前一月。

    改图抄来的行已经换成新零件号，落在新号的身份上。这里不要再按工艺行 id 丢掉。
    """
    part = StampingPartService().get_by_id(db, part_id)
    orders = _order_repo.list_success_for_identity(
        db,
        location=part.location,
        stamping_supplier=part.stamping_supplier or "",
        vehicle_model=part.vehicle_model,
        part_number=part.part_number,
    )
    records: list[MaterialChangeRecordVO] = []
    for index, order in enumerate(orders):
        nxt = orders[index + 1] if index + 1 < len(orders) else None
        valid_until_year: int | None = None
        valid_until_month: int | None = None
        if nxt is not None:
            valid_until_year, valid_until_month = previous_month(
                nxt.effective_year, nxt.effective_month
            )
        log_row = _log_repo.get_by_id(db, order.upload_log_id)
        original_filename = log_row.original_filename if log_row else ""
        records.append(
            MaterialChangeRecordVO(
                change_version=order.change_version,
                effective_year=order.effective_year,
                effective_month=order.effective_month,
                valid_until_year=valid_until_year,
                valid_until_month=valid_until_month,
                before_material=order.before_material,
                after_material=order.after_material,
                before_thickness=order.before_thickness,
                after_thickness=order.after_thickness,
                stamping_supplier=order.stamping_supplier,
                original_filename=original_filename,
                upload_log_id=order.upload_log_id,
            )
        )
    return records
