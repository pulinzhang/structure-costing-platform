"""
成品月核价 — 列表 / 明细 / 审核 / 导出 API
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.exceptions.base import BusinessException
from app.schemas.common.page_result import PageResult
from app.schemas.dto.l0_assembly_cost_dto import (
    L0AssemblyCostBatchApproveDTO,
    L0AssemblyCostBatchDeleteDTO,
    L0AssemblyCostBatchReverseDTO,
    L0AssemblyCostQuery,
)
from app.schemas.vo.l0_assembly_cost_vo import (
    L0AssemblyCostBatchResultVO,
    L0AssemblyCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.l0_assembly_cost.l0_assembly_cost_export_service import (
    L0AssemblyCostExportService,
)
from app.services.costing.l0_assembly_cost.l0_assembly_cost_service import (
    L0AssemblyCostService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/l0-assembly-costs",
    tags=["成品核价"],
)

_service = L0AssemblyCostService()
_export_service = L0AssemblyCostExportService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[L0AssemblyCostVO]],
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_VIEW)),
) -> ApiResponse[PageResult[L0AssemblyCostVO]]:
    query = L0AssemblyCostQuery(
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        part_number=part_number,
        audit_status=audit_status,
        calc_status=calc_status,
        skip=skip,
        limit=limit,
    )
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=(skip // limit) + 1 if limit else 1,
        page_size=limit,
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
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_EXPORT)),
) -> StreamingResponse:
    """按当前筛选导出成品核价 Excel（主表 + 材料明细 + 间接费用）。"""
    if not any(
        [
            year,
            month,
            location,
            vehicle_model,
            bom_version,
            part_number,
            audit_status,
            calc_status,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一个筛选条件后再导出",
        )

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
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get(
    "/{cost_id}",
    response_model=ApiResponse[L0AssemblyCostVO],
)
def get_cost(
    cost_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_VIEW)),
) -> ApiResponse[L0AssemblyCostVO]:
    row = _service.get_by_id(db, cost_id)
    if row is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ApiResponse.ok(data=row)


@router.post(
    "/batch-delete",
    response_model=ApiResponse[L0AssemblyCostBatchResultVO],
)
def batch_delete(
    dto: L0AssemblyCostBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_DELETE)),
) -> ApiResponse[L0AssemblyCostBatchResultVO]:
    try:
        result = _service.batch_delete(db, dto, current_user=current_user)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ApiResponse.ok(data=result, message=result.message or "删除完成")


@router.post(
    "/batch-approve",
    response_model=ApiResponse[L0AssemblyCostBatchResultVO],
)
def batch_approve(
    dto: L0AssemblyCostBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_APPROVE)),
) -> ApiResponse[L0AssemblyCostBatchResultVO]:
    try:
        result = _service.batch_approve(db, dto, current_user=current_user)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ApiResponse.ok(data=result, message=result.message or "审核完成")


@router.post(
    "/batch-reverse",
    response_model=ApiResponse[L0AssemblyCostBatchResultVO],
)
def batch_reverse(
    dto: L0AssemblyCostBatchReverseDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_REVERSE)),
) -> ApiResponse[L0AssemblyCostBatchResultVO]:
    try:
        result = _service.batch_reverse(db, dto, current_user=current_user)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ApiResponse.ok(data=result, message=result.message or "反审核完成")
