"""焊接工艺拆解列表 HUD：工艺数=0 钻取不掏空大盘。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownQuery,
)
from app.services.bom.welding_process_breakdown.service import (
    BomWeldingProcessBreakdownService,
)


@patch("app.services.bom.welding_process_breakdown.query.BomPeriodService")
@patch("app.services.bom.welding_process_breakdown.service.LocationService")
@patch("app.services.bom.welding_process_breakdown.service.VehicleModelService")
def test_paginate_hud_ignores_zero_process_drilldown(
    mock_vehicle_cls: MagicMock,
    mock_location_cls: MagicMock,
    mock_bom_cls: MagicMock,
) -> None:
    mock_location = mock_location_cls.return_value
    mock_location.list_registered.return_value = []
    mock_location.expand_for_query.return_value = ["芜湖"]
    mock_vehicle_cls.return_value.list_filter_codes.return_value = []
    mock_bom_cls.return_value.list_l0_versions.return_value = []
    mock_bom_cls.return_value.node_ids_for_l0_version.return_value = None

    service = BomWeldingProcessBreakdownService()
    service.repository = MagicMock()
    service.repository.paginate.return_value = ([], 2)
    service.repository.get_distinct_customer_names.return_value = []
    service.repository.summarize_by_filters.return_value = {
        "total_count": 89,
        "pending_count": 80,
        "approved_count": 9,
        "l0_count": 40,
    }
    service.repository.count_by_filters.return_value = 3

    _vos, total, filters = service.paginate(
        MagicMock(),
        BomWeldingProcessBreakdownQuery(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            process_line_count_eq=0,
            page=1,
            size=10,
        ),
    )

    assert total == 2
    assert service.repository.paginate.call_args.kwargs["process_line_count_eq"] == 0
    hud_kw = service.repository.summarize_by_filters.call_args.kwargs
    assert "process_line_count_eq" not in hud_kw
    assert hud_kw["locations"] == ["芜湖"]
    assert filters["summary"]["total_count"] == 89
    assert filters["summary"]["l0_zero_process_count"] == 3
    zero_kw = service.repository.count_by_filters.call_args.kwargs
    assert zero_kw["level"] == 0
    assert zero_kw["process_line_count_eq"] == 0
