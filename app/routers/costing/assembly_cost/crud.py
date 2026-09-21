"""
成品月核价 — 列表 / 明细 / 审核 / 导出 API
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.operation_log.context import set_request_audit_scope
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.assembly_cost_dto import (
    AssemblyCostBatchApproveDTO,
    AssemblyCostBatchDeleteDTO,
    AssemblyCostBatchReverseDTO,
    AssemblyCostQuery,
    AssemblyCostView,
)
from app.schemas.vo.assembly_cost_restore_vo import AssemblyCostRestoreVO
from app.schemas.vo.assembly_cost_vo import (
    AssemblyCostBatchResultVO,
    AssemblyCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.assembly_cost.export.service import (
    AssemblyCostExportService,
)
from app.services.costing.assembly_cost.restore.service import (
    AssemblyCostRestoreService,
)
from app.services.costing.assembly_cost.service import (
    AssemblyCostService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/assembly-costs",
    tags=["总成核价"],
)

_service = AssemblyCostService()
_export_service = AssemblyCostExportService()
_restore_service = AssemblyCostRestoreService()


def _bind_restore_audit_scope(request: Request, row: AssemblyCostRestoreVO) -> None:
    set_request_audit_scope(
        request,
        {
            "location": row.location,
            "part_number": row.part_number,
            "year": str(row.year),
            "month": str(row.month),
        },
    )


@router.get(
    "",
    response_model=ApiResponse[PageResult[AssemblyCostVO]],
)
def list_costs(
    year: int | None = Query(None),
    month: int | None = Query(None),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    part_number: str | None = Query(None),
    audit_status: str | None = Query(None),
    calc_status: str | None = Query(None),
    view: AssemblyCostView = Query("finance"),
    level: int | None = Query(None),
    object_kind: str | None = Query(None),
    confirm_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_VIEW)),
) -> ApiResponse[PageResult[AssemblyCostVO]]:
    query = AssemblyCostQuery(
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        part_number=part_number,
        audit_status=audit_status,
        calc_status=calc_status,
        view=view,
        level=level,
        object_kind=object_kind,
        confirm_status=confirm_status,
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


@router.get("/export-download")
def export_download(
    year: int | None = Query(None, ge=2000, le=2100, description="年度"),
    month: int | None = Query(None, ge=1, le=12, description="月份"),
    location: str | None = Query(None, description="基地"),
    vehicle_model: str | None = Query(None, description="项目"),
    bom_version: str | None = Query(None, description="版本"),
    part_number: str | None = Query(None, description="零件号"),
    audit_status: str | None = Query(None, description="审核状态"),
    calc_status: str | None = Query(None, description="核算状态"),
    view: AssemblyCostView = Query("finance"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_EXPORT)),
) -> StreamingResponse:
    """按当前筛选导出成品核价 Excel（主表 + 材料明细 + 间接费用）。"""
    content, filename = _export_service.export(
        db,
        year=year,
        month=month,
        location=location.strip() if location else None,
        vehicle_model=vehicle_model.strip() if vehicle_model else None,
        bom_version=bom_version.strip() if bom_version else None,
        part_number=part_number.strip() if part_number else None,
        audit_status=audit_status.strip() if audit_status else None,
        calc_status=calc_status.strip() if calc_status else None,
        view=view,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/restore",
    response_model=ApiResponse[AssemblyCostRestoreVO],
)
def get_restore_by_part(
    request: Request,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    part_number: str = Query(..., min_length=1),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    view: str = Query("finance"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_VIEW)),
) -> ApiResponse[AssemblyCostRestoreVO]:
    row = _restore_service.get_restore_by_part(
        db,
        year=year,
        month=month,
        part_number=part_number,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        view=view,
    )
    _bind_restore_audit_scope(request, row)
    return ApiResponse.ok(data=row)


@router.get(
    "/{cost_id:int}/restore",
    response_model=ApiResponse[AssemblyCostRestoreVO],
)
def get_restore(
    request: Request,
    cost_id: int,
    view: str = Query("finance"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_VIEW)),
) -> ApiResponse[AssemblyCostRestoreVO]:
    row = _restore_service.get_restore(db, cost_id, view=view)
    _bind_restore_audit_scope(request, row)
    return ApiResponse.ok(data=row)


@router.get(
    "/{cost_id:int}",
    response_model=ApiResponse[AssemblyCostVO],
)
def get_cost(
    cost_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_VIEW)),
) -> ApiResponse[AssemblyCostVO]:
    row = _service.get_by_id(db, cost_id)
    return ApiResponse.ok(data=row)


@router.post(
    "/batch-delete",
    response_model=ApiResponse[AssemblyCostBatchResultVO],
)
def batch_delete(
    dto: AssemblyCostBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_DELETE)),
) -> ApiResponse[AssemblyCostBatchResultVO]:
    result = _service.batch_delete(db, dto, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message or "删除完成")


@router.post(
    "/batch-approve",
    response_model=ApiResponse[AssemblyCostBatchResultVO],
)
def batch_approve(
    dto: AssemblyCostBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_APPROVE)),
) -> ApiResponse[AssemblyCostBatchResultVO]:
    result = _service.batch_approve(db, dto, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message or "审核完成")


@router.post(
    "/batch-reverse",
    response_model=ApiResponse[AssemblyCostBatchResultVO],
)
def batch_reverse(
    dto: AssemblyCostBatchReverseDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_REVERSE)),
) -> ApiResponse[AssemblyCostBatchResultVO]:
    result = _service.batch_reverse(db, dto, current_user=current_user)
    return ApiResponse.ok(data=result, message=result.message or "反审核完成")
