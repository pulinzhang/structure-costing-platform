"""焊接单价标准工艺目录门禁。"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from openpyxl import Workbook

from app.common.bom.welding_standard_process import validate_welding_unit_price_catalog
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.bom.welding_unit_price_parser import parse_welding_unit_price_excel
from app.schemas.dto.bom_welding_unit_price_dto import BomWeldingUnitPriceCreate
from app.services.bom.welding_unit_price.importing.service import (
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


@patch("app.services.bom.welding_unit_price.importing.service.LocationService")
def test_import_aborts_on_catalog_error(mock_location_cls: MagicMock) -> None:
    mock_location_cls.return_value.require_enabled.return_value = "青岛"
    content = _xlsx_bytes(
        [
            ("焊点", "个", 0.13, ""),
            ("拆边/点焊胶", "MM", 0.001, ""),
        ]
    )
    service = BomWeldingUnitPriceImportService()
    with pytest.raises(BusinessException, match="导入中止"):
        service.import_excel(
            db=None,  # type: ignore[arg-type]
            file_content=content,
            filename="bad.xlsx",
            location="青岛",
            year=2025,
            current_user=None,  # type: ignore[arg-type]
        )


@patch("app.services.bom.welding_unit_price.importing.service.LocationService")
def test_import_rejects_workbook_when_price_invalid(
    mock_location_cls: MagicMock,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "UPLOAD_DIR", tmp_path)
    mock_location_cls.return_value.require_enabled.return_value = "青岛"
    content = _xlsx_bytes(
        [
            ("焊点", "个", Decimal("0.1300"), ""),
            ("铆接", "个", "不是数字", ""),
        ]
    )
    service = BomWeldingUnitPriceImportService()
    with pytest.raises(BusinessException, match="整本未导入") as raised:
        service.import_excel(
            db=None,  # type: ignore[arg-type]
            file_content=content,
            filename="mixed.xlsx",
            location="青岛",
            year=2025,
            current_user=None,  # type: ignore[arg-type]
        )
    message = str(raised.value)
    assert "「费用」填了「不是数字」" in message
    assert "请改成大于等于 0 的数字" in message
    assert "\n· " in message


def test_list_standard_catalog_includes_hemming() -> None:
    items = BomWeldingUnitPriceImportService().list_standard_catalog()
    names = {item.item_name for item in items}
    assert "折边/点焊胶" in names
    hemming = next(item for item in items if item.item_name == "折边/点焊胶")
    assert hemming.unit == "MM"
