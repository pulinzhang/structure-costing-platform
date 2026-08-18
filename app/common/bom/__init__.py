"""BOM 公共能力（制造类别、焊接标准工艺名等）"""

from app.common.bom.manufacturing_category import (
    MANUFACTURING_CATEGORIES,
    resolve_manufacturing_category,
    short_part_number_digits,
    short_weld_part_number,
)
from app.common.bom.welding_standard_process import (
    WeldingStandardProcessName,
    all_standard_process_names,
    resolve_standard_process_name,
)

__all__ = [
    "MANUFACTURING_CATEGORIES",
    "WeldingStandardProcessName",
    "all_standard_process_names",
    "resolve_manufacturing_category",
    "resolve_standard_process_name",
    "short_part_number_digits",
    "short_weld_part_number",
]
