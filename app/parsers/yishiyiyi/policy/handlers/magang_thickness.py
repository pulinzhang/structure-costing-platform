"""马钢厚度解析：默认厚度块装配。"""

from __future__ import annotations

from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.parsers.yishiyiyi.policy.handlers.base_handler.base_handler import BaseSheetHandler


def parse_thickness_fixed(
    handler: BaseSheetHandler, sheet: Worksheet, steel_mill: str
) -> list[Any]:
    """复用默认厚度块定位，再交给 PolicyAssembler 装配。"""
    blocks = handler.find_default_thickness_blocks(sheet, steel_mill)
    policies: list[Any] = []
    for block in blocks:
        policies.extend(handler.assembler.build_policies_from_block(sheet, steel_mill, block))
    return policies
