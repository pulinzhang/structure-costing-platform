"""冲压零件列表/导出按 Excel 序号，禁止 id。"""

from app.models.stamping import StampingPart
from app.repositories.stamping.part.filters import _PART_LIST_ORDER


def test_part_list_order_is_location_supplier_seq_not_id() -> None:
    keys = [column.key for column in _PART_LIST_ORDER]
    assert keys == [
        "location",
        "vehicle_model",
        "stamping_supplier",
        "seq_no",
        "part_number",
    ]
    assert StampingPart.id.key not in keys
    assert "version" not in keys
