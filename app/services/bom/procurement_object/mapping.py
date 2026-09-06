"""采购对象清单 — ORM 行转 VO。"""

from app.models.bom.procurement_object import BomProcurementObject
from app.schemas.vo.bom_procurement_object_vo import BomProcurementObjectVO


def to_object_vo(row: BomProcurementObject) -> BomProcurementObjectVO:
    header = row.object_list
    vo = BomProcurementObjectVO.model_validate(row)
    return vo.model_copy(
        update={
            "location": header.location,
            "vehicle_model": header.vehicle_model,
            "bom_version": header.bom_version,
            "source_filename": header.source_filename,
            "qa_passed": header.qa_passed,
        }
    )
