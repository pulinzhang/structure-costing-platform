"""BOM 清单头信息解析。"""

from __future__ import annotations

import re

from app.parsers.bom.models import BomParsedMeta
from app.parsers.bom.value_parser import cell_value, parse_date, to_text


def parse_bom_meta(ws) -> BomParsedMeta:
    """从工作表前几行解析清单头信息。"""
    meta = BomParsedMeta()
    meta.title = to_text(cell_value(ws, 1, 1))

    # Row2: 编制部门 / 编制日期 / 版本 / 编号
    row2 = " ".join(str(cell_value(ws, 2, c) or "") for c in range(1, 24))
    dept_match = re.search(r"编制部门[:：]\s*([^\s]+)", row2)
    if dept_match:
        meta.prepare_dept = dept_match.group(1).strip()
    ver_match = re.search(r"版本[:：]\s*([^\s]+)", row2)
    if ver_match:
        meta.bom_version = ver_match.group(1).strip()
    doc_match = re.search(r"编号[:：]\s*([^\s]*)", row2)
    if doc_match and doc_match.group(1):
        meta.doc_no = doc_match.group(1).strip() or None
    meta.doc_date = parse_date(row2)

    # Row3 meta fields may be split across columns
    row3_parts: list[str] = []
    for col in range(1, 24):
        value = to_text(cell_value(ws, 3, col))
        if value:
            row3_parts.append(value)
    row3 = " ".join(row3_parts)

    vm = re.search(r"项目代号[:：]?\s*([A-Za-z0-9\-]+)", row3)
    if vm:
        meta.vehicle_model = vm.group(1).strip()
    cat = re.search(r"产品类别[:：]?\s*(\S+)", row3)
    if cat:
        meta.product_category = cat.group(1).strip()
    cust = re.search(r"顾客名称[:：]?\s*(\S+)", row3)
    if cust:
        meta.customer_name = cust.group(1).strip()
    if "批量生产清单" in row3 and "■" in row3.split("批量生产清单")[0][-3:]:
        meta.stage = "mass"
    elif "初始清单" in row3:
        if re.search(r"■\s*批量生产清单", row3):
            meta.stage = "mass"
        else:
            meta.stage = "initial"
    rev = re.search(r"修订日期[:：]?\s*([0-9年月日./\-]+)", row3)
    if rev:
        meta.revision_date = parse_date(rev.group(1))

    if not meta.bom_version:
        meta.bom_version = "V1"
    if not meta.vehicle_model:
        meta.vehicle_model = "UNKNOWN"

    return meta
