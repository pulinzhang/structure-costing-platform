"""焊接费列表 HUD：按筛选全量汇总，缺单价钻取不掏空大盘。"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeQuery
from app.schemas.vo.bom_welding_fee_vo import WeldingFeeListSummaryVO
from app.services.bom.welding_fee.service import BomWeldingFeeService


def _full_summary() -> dict[str, int | Decimal]:
    return {
        "total_count": 89,
        "total_fee": Decimal("128.5000"),
        "pending_count": 80,
        "approved_count": 9,
        "partial_count": 3,
        "failed_count": 0,
        "missing_price_count": 0,
    }


def test_list_fees_hud_summary_is_full_filter_not_page() -> None:
    service = BomWeldingFeeService()
    service.fee_repo = MagicMock()
    service.breakdown_repo = MagicMock()
    page_row = MagicMock()
    page_row.source_breakdown_node_id = None
    page_row.weld_info_raw = "x"
    service.fee_repo.paginate.return_value = ([page_row], 89)
    service.fee_repo.summarize_by_filters.return_value = _full_summary()
    service._to_vos = MagicMock(return_value=[])

    _vos, total, filters = service.list_fees(
        MagicMock(),
        BomWeldingFeeQuery(year=2026, location="芜湖", page=2, size=10),
    )

    assert total == 89
    paginate_kw = service.fee_repo.paginate.call_args.kwargs
    assert paginate_kw["skip"] == 10
    assert paginate_kw["limit"] == 10
    summary = filters["summary"]
    assert isinstance(summary, WeldingFeeListSummaryVO)
    assert summary.total_count == 89
    assert summary.total_fee == Decimal("128.5000")
    assert summary.pending_count == 80


def test_list_fees_hud_ignores_partial_drilldown() -> None:
    service = BomWeldingFeeService()
    service.fee_repo = MagicMock()
    service.breakdown_repo = MagicMock()
    service.fee_repo.paginate.return_value = ([], 3)
    service.fee_repo.summarize_by_filters.return_value = _full_summary()

    _vos, total, filters = service.list_fees(
        MagicMock(),
        BomWeldingFeeQuery(
            year=2026,
            location="芜湖",
            page=1,
            size=10,
            calc_status="partial",
        ),
    )

    assert total == 3
    assert service.fee_repo.paginate.call_args.kwargs["calc_status"] == "partial"
    hud_kw = service.fee_repo.summarize_by_filters.call_args.kwargs
    assert "calc_status" not in hud_kw
    assert hud_kw["year"] == 2026
    assert hud_kw["location"] == "芜湖"
    assert filters["summary"].partial_count == 3
    assert filters["summary"].total_count == 89


def test_list_fees_filters_l0_and_l1_levels() -> None:
    service = BomWeldingFeeService()
    service.fee_repo = MagicMock()
    service.breakdown_repo = MagicMock()
    service.fee_repo.paginate.return_value = ([], 2)
    service.fee_repo.summarize_by_filters.return_value = _full_summary()
    service._to_vos = MagicMock(return_value=[])

    _vos, _total, filters = service.list_fees(
        MagicMock(),
        BomWeldingFeeQuery(year=2026, location="青岛", levels="0,1", page=1, size=10),
    )

    assert service.fee_repo.paginate.call_args.kwargs["levels"] == [0, 1]
    assert "level" not in service.fee_repo.paginate.call_args.kwargs
    assert service.fee_repo.summarize_by_filters.call_args.kwargs["levels"] == [0, 1]
    assert filters["levels"] == [0, 1]


def test_list_fees_single_level_still_works() -> None:
    service = BomWeldingFeeService()
    service.fee_repo = MagicMock()
    service.breakdown_repo = MagicMock()
    service.fee_repo.paginate.return_value = ([], 1)
    service.fee_repo.summarize_by_filters.return_value = _full_summary()
    service._to_vos = MagicMock(return_value=[])

    service.list_fees(
        MagicMock(),
        BomWeldingFeeQuery(year=2026, location="青岛", level=0, page=1, size=10),
    )

    assert service.fee_repo.paginate.call_args.kwargs["levels"] == [0]
