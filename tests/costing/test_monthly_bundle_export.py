"""月度核对导出：成品块只出树根。"""

from unittest.mock import MagicMock, patch

from app.services.costing.monthly_bundle_export.monthly_bundle_export_service import (
    MonthlyBundleExportService,
)


def _stub_sheet_writers(service: MonthlyBundleExportService) -> None:
    service.assembly.write_to_workbook = MagicMock(return_value=("成品核价一览", 1))
    service.part_cost.write_to_workbook = MagicMock(return_value=("冲压核价结果", 0))
    service.process_fee.write_to_workbook = MagicMock(return_value=("冲压加工费", 0))
    service.steel_price.write_to_workbook = MagicMock(return_value=("钢材联动", 0))
    service.annual_part_price.write_to_workbook = MagicMock(return_value=("年度零件价", 0))
    service.packaging.write_to_workbook = MagicMock(return_value=("包装运输费", 0))
    service.welding_unit_price.write_to_workbook = MagicMock(return_value=("焊接单价", 0))


def test_bundle_always_exports_finance_tree_roots() -> None:
    service = MonthlyBundleExportService()
    _stub_sheet_writers(service)
    with (
        patch(
            "app.services.costing.monthly_bundle_export.monthly_bundle_export_service.write_cover_sheet",
            return_value="封皮·核价说明",
        ),
        patch(
            "app.services.costing.monthly_bundle_export.monthly_bundle_export_service.workbook_to_xlsx_bytes",
            return_value=b"xlsx",
        ),
    ):
        service.export(
            MagicMock(),
            year=2025,
            month=12,
            location="青岛",
            vehicle_model="T2AA",
            bom_version="D/09",
            current_user=MagicMock(),
        )
    assert service.assembly.write_to_workbook.call_args.kwargs["view"] == "finance"
    assert "stamping_supplier" not in service.part_cost.write_to_workbook.call_args.kwargs
    assert "stamping_supplier" not in service.process_fee.write_to_workbook.call_args.kwargs
