"""采购价格 — 列表 / 预检 / 导出。"""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.procurement_contract_report_dto import ProcurementContractReportQuery
from app.schemas.vo.procurement_contract_report_vo import (
    ProcurementContractOpenDefaultsVO,
    ProcurementContractReportPrepVO,
    ProcurementContractReportRowVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.procurement_contract_report.export.orchestrator import (
    ProcurementContractReportExportOrchestrator,
)
from app.services.costing.procurement_contract_report.service import (
    ProcurementContractReportService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/procurement-contract-report",
    tags=["采购价格协议"],
)

_service = ProcurementContractReportService()
_export_orchestrator = ProcurementContractReportExportOrchestrator()


def _query_from_params(
    *,
    location: str,
    vehicle_model: str,
    bom_version: str | None,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
    supplier_name: str | None,
    view: Literal["procurement", "assembly"] = "procurement",
    keyword: str | None = None,
    page: int,
    size: int,
) -> ProcurementContractReportQuery:
    return ProcurementContractReportQuery(
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        view=view,
        supplier_name=supplier_name,
        keyword=keyword,
        page=page,
        size=size,
    )


@router.get(
    "",
    response_model=ApiResponse[PageResult[ProcurementContractReportRowVO]],
    summary="分页查询采购价格协议",
)
def list_report(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str | None = Query(None),
    start_year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    start_month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    end_year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    end_month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    supplier_name: str | None = Query(None),
    view: Literal["procurement", "assembly"] = Query("procurement"),
    keyword: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.PROCUREMENT_CONTRACT_REPORT_VIEW)),
) -> ApiResponse[PageResult[ProcurementContractReportRowVO]]:
    query = _query_from_params(
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        view=view,
        supplier_name=supplier_name,
        keyword=keyword,
        page=page,
        size=size,
    )
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=page,
        page_size=size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get(
    "/filters/defaults",
    response_model=ApiResponse[ProcurementContractOpenDefaultsVO],
    summary="获取采购价格协议默认筛选",
)
def list_open_defaults(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.PROCUREMENT_CONTRACT_REPORT_VIEW)),
) -> ApiResponse[ProcurementContractOpenDefaultsVO]:
    return ApiResponse.ok(data=_service.get_open_defaults(db))


@router.get(
    "/prep", response_model=ApiResponse[ProcurementContractReportPrepVO], summary="预检采购价格协议"
)
def prep_report(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str | None = Query(None),
    start_year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    start_month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    end_year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    end_month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    supplier_name: str | None = Query(None),
    view: Literal["procurement", "assembly"] = Query("procurement"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.PROCUREMENT_CONTRACT_REPORT_VIEW)),
) -> ApiResponse[ProcurementContractReportPrepVO]:
    query = _query_from_params(
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        view=view,
        supplier_name=supplier_name,
        page=1,
        size=20,
    )
    return ApiResponse.ok(data=_service.prep(db, query))


@router.get("/export", summary="导出采购价格协议")
def export_report(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str | None = Query(None),
    start_year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    start_month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    end_year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    end_month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    supplier_name: str | None = Query(None),
    view: Literal["procurement", "assembly"] = Query("procurement"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.PROCUREMENT_CONTRACT_REPORT_EXPORT)),
) -> StreamingResponse:
    query = _query_from_params(
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        view=view,
        supplier_name=supplier_name,
        page=1,
        size=20,
    )
    content, filename = _export_orchestrator.export(db, query)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
