"""基准价格导出筛选字段。"""

from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceExportPreviewQuery,
    SteelBasePriceExportQuery,
)


def test_base_price_export_query_filters():
    assert set(SteelBasePriceExportQuery.model_fields) == {
        "year",
        "month",
        "location",
        "steel_mill",
        "category_name",
        "grade",
    }
    assert "page" in SteelBasePriceExportPreviewQuery.model_fields
    assert "size" in SteelBasePriceExportPreviewQuery.model_fields
