"""焊接单价标准工艺目录门禁。"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.common.bom.welding_standard_process import validate_welding_unit_price_catalog
from app.parsers.bom.welding_unit_price_parser import parse_welding_unit_price_excel
from app.schemas.dto.bom_welding_unit_price_dto import BomWeldingUnitPriceCreate
from app.services.bom.welding_unit_price_import_service import (
    BomWeldingUnitPriceImportService,
)


def _xlsx_bytes(rows: list[tuple[str, str, object, str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.append(["名称", "单位", "费用", "备注"])
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_validate_rejects_typo_hemming_name() -> None:
    with pytest.raises(ValueError, match="不属于焊接标准工艺目录"):
        validate_welding_unit_price_catalog("拆边/点焊胶", "MM")


def test_validate_accepts_catalog_name_and_unit() -> None:
    validate_welding_unit_price_catalog("折边/点焊胶", "mm")


def test_parser_skips_non_catalog_name() -> None:
    content = _xlsx_bytes(
        [
            ("焊点", "个", 0.13, ""),
            ("拆边/点焊胶", "MM", 0.001, ""),
        ]
    )
    result = parse_welding_unit_price_excel(content)
    assert len(result.rows) == 1
    assert result.rows[0].item_name == "焊点"
    assert any("不属于焊接标准工艺目录" in err for err in result.errors)


def test_create_dto_rejects_non_catalog_name() -> None:
    with pytest.raises(ValueError, match="不属于焊接标准工艺目录"):
        BomWeldingUnitPriceCreate(
            location="青岛",
            year=2025,
            item_name="拆边/点焊胶",
            unit="MM",
            unit_price=Decimal("0.0010"),
        )


def test_import_aborts_on_catalog_error() -> None:
    content = _xlsx_bytes(
        [
            ("焊点", "个", 0.13, ""),
            ("拆边/点焊胶", "MM", 0.001, ""),
        ]
    )
    service = BomWeldingUnitPriceImportService()
    with pytest.raises(ValueError, match="导入中止"):
        service.import_excel(
            db=None,  # type: ignore[arg-type]
            file_content=content,
            filename="bad.xlsx",
            location="青岛",
            year=2025,
            current_user=None,  # type: ignore[arg-type]
        )


def test_list_standard_catalog_includes_hemming() -> None:
    items = BomWeldingUnitPriceImportService().list_standard_catalog()
    names = {item.item_name for item in items}
    assert "折边/点焊胶" in names
    hemming = next(item for item in items if item.item_name == "折边/点焊胶")
    assert hemming.unit == "MM"
