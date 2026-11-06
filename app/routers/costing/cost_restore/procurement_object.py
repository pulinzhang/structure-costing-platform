"""成本还原 — 采购对象查询与导出。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.period import COSTING_YEAR_MAX, COSTING_YEAR_MIN, MONTH_MAX, MONTH_MIN
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.cost_restore_procurement_object_dto import CostRestoreProcurementObjectQuery
from app.schemas.vo.cost_restore_procurement_object_vo import (
    CostRestoreDefaultsVO,
    CostRestoreLineVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.cost_restore.procurement_object.export import (
    CostRestoreProcurementObjectExport,
)
from app.services.costing.cost_restore.procurement_object.service import (
    CostRestoreProcurementObjectService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/cost-restore/procurement-objects",
    tags=["成本还原-采购对象"],
)

_service = CostRestoreProcurementObjectService()
_export = CostRestoreProcurementObjectExport(_service)


def _query_from_params(
    *,
    location: str,
    year: int,
    month: int,
    vehicle_model: str | None,
    supplier_name: str | None,
    page: int,
    size: int,
) -> CostRestoreProcurementObjectQuery:
    return CostRestoreProcurementObjectQuery(
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
        supplier_name=supplier_name,
        page=page,
        size=size,
    )


@router.get(
    "/defaults",
    response_model=ApiResponse[CostRestoreDefaultsVO],
    summary="打开采购对象成本还原时的默认条件",
)
def read_defaults(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COST_RESTORE_PROCUREMENT_OBJECT_VIEW)),
) -> ApiResponse[CostRestoreDefaultsVO]:
    return ApiResponse.ok(data=_service.defaults(db))


@router.get("/export", summary="导出采购对象成本还原")
def export_procurement_objects(
    location: str = Query(..., min_length=1),
    year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    vehicle_model: str | None = Query(None),
    supplier_name: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COST_RESTORE_PROCUREMENT_OBJECT_EXPORT)),
) -> StreamingResponse:
    query = _query_from_params(
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
        supplier_name=supplier_name,
        page=1,
        size=10,
    )
    content, filename = _export.export(db, query)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "",
    response_model=ApiResponse[PageResult[CostRestoreLineVO]],
    summary="查询采购对象成本还原",
)
def list_procurement_objects(
    location: str = Query(..., min_length=1),
    year: int = Query(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX),
    month: int = Query(..., ge=MONTH_MIN, le=MONTH_MAX),
    vehicle_model: str | None = Query(None),
    supplier_name: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.COST_RESTORE_PROCUREMENT_OBJECT_VIEW)),
) -> ApiResponse[PageResult[CostRestoreLineVO]]:
    query = _query_from_params(
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
        supplier_name=supplier_name,
        page=page,
        size=size,
    )
    items, total, scope = _service.query_page(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=page,
        page_size=size,
        filters=scope.model_dump(),
    )
