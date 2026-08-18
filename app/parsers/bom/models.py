"""BOM 解析结果数据模型（纯数据结构，无逻辑）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class BomParsedMeta:
    """清单头信息（基地由导入方传入，不从 Excel 读）"""

    title: str | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    product_category: str | None = None
    customer_name: str | None = None
    stage: str = "initial"
    prepare_dept: str | None = None
    doc_date: date | None = None
    revision_date: date | None = None
    doc_no: str | None = None


@dataclass
class BomParsedNode:
    """解析出的树节点（parent_index 指向同列表中的父节点下标）"""

    level: int
    parent_index: int | None
    sort_no: int
    seq_no: int | None = None
    internal_number: str | None = None
    part_number: str = ""
    part_name: str | None = None
    qty: Decimal | None = None
    qty_unit: str = "pcs"
    qty_text: str | None = None
    node_role: str = "make"
    is_supply_unit: bool = False
    material: str | None = None
    thickness_mm: Decimal | None = None
    thickness_text: str | None = None
    material_mill: str | None = None
    part_weight: Decimal | None = None
    gauge_developed: str | None = None
    weld_info: str | None = None
    remark: str | None = None
    source_row: int | None = None
    sketch_bytes: bytes | None = None


@dataclass
class BomParseResult:
    meta: BomParsedMeta
    nodes: list[BomParsedNode] = field(default_factory=list)
    sheet_name: str | None = None
    image_count: int = 0
