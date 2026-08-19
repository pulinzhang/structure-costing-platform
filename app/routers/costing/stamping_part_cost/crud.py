"""
冲压零件价格核算管理 API
列表查询、手工改价、批量审核/删除、导出
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.exceptions.base import BusinessException
from app.schemas.common.page_result import PageResult
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostBatchApproveDTO,
    StampingPartCostBatchReverseAuditDTO,
    StampingPartCostDeleteDTO,
    StampingPartCostManualUnitCostDTO,
    StampingPartCostQuery,
)
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostBatchAuditResultVO,
    StampingPartCostBatchDeleteResultVO,
    StampingPartCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.stamping_part_cost_export_service import (
    StampingPartCostExportService,
)
from app.services.costing.stamping_part_cost.stamping_part_cost_service import (
    StampingPartCostService,
)
from app.utils.response import ApiResponse


router = APIRouter(
    prefix="/api/costing/stamping-part-cost",
    tags=["冲压零件价格核算"],
)

_service = StampingPartCostService()
_export_service = StampingPartCostExportService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[StampingPartCostVO]],
)
def list_costs(
    query: StampingPartCostQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_VIEW)),
) -> ApiResponse[PageResult[StampingPartCostVO]]:
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/export-download")
def export_download(
    year: int | None = Query(None, ge=2000, le=2100, description="年度"),
    month: int | None = Query(None, ge=1, le=12, description="月份"),
    location: str | None = Query(None, description="基地"),
    stamping_supplier: str | None = Query(None, description="冲压工厂"),
    vehicle_model: str | None = Query(None, description="车型"),
    version: str | None = Query(None, description="版本"),
    part_number: str | None = Query(None, description="零件号"),
    audit_status: str | None = Query(None, description="审核状态"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出冲压零件核价结果 Excel（材料费 + 加工费）。"""
    if not any(
        [
            year,
            month,
            location,
            stamping_supplier,
            vehicle_model,
            version,
            part_number,
            audit_status,
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
        stamping_supplier=stamping_supplier.strip() if stamping_supplier else None,
        vehicle_model=vehicle_model.strip() if vehicle_model else None,
        version=version.strip() if version else None,
        part_number=part_number.strip() if part_number else None,
        audit_status=audit_status.strip() if audit_status else None,
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
    response_model=ApiResponse[StampingPartCostVO],
)
def get_cost(
    cost_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_VIEW)),
) -> ApiResponse[StampingPartCostVO]:
    row = _service.get_by_id(db, cost_id)
    if not row:
        raise HTTPException(status_code=404, detail="核算记录不存在")
    return ApiResponse.ok(data=row)


@router.patch(
    "/{cost_id}",
    response_model=ApiResponse[StampingPartCostVO],
)
def update_manual_unit_cost(
    cost_id: int,
    dto: StampingPartCostManualUnitCostDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_UPDATE)),
) -> ApiResponse[StampingPartCostVO]:
    try:
        row = _service.update_manual_unit_cost(
            db, cost_id, dto, current_user=current_user
        )
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ApiResponse.updated(data=row, message="最终成本已保存")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[StampingPartCostBatchDeleteResultVO],
)
def batch_delete_costs(
    dto: StampingPartCostDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_DELETE)),
) -> ApiResponse[StampingPartCostBatchDeleteResultVO]:
    try:
        result = _service.batch_delete(db, dto)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    message = f"已删除 {result.deleted_count} 条"
    if result.skipped_approved_count:
        message += f"，跳过已审核 {result.skipped_approved_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-approve",
    response_model=ApiResponse[StampingPartCostBatchAuditResultVO],
)
def batch_approve_costs(
    dto: StampingPartCostBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_APPROVE)),
) -> ApiResponse[StampingPartCostBatchAuditResultVO]:
    try:
        result = _service.batch_approve(db, dto, current_user=current_user)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    message = f"已审核通过 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[StampingPartCostBatchAuditResultVO],
)
def batch_reverse_audit_costs(
    dto: StampingPartCostBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_REVERSE)),
) -> ApiResponse[StampingPartCostBatchAuditResultVO]:
    try:
        result = _service.batch_reverse_audit(db, dto, current_user=current_user)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    message = f"已反审核 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)
