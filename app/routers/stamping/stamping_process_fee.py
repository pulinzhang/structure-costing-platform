"""
冲压加工费路由
异步计算 + 计算日志 + 列表审核删除
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common import DeletedCountVO, PageResult
from app.schemas.dto.stamping_process_fee_dto import (
    StampingProcessFeeBatchApproveDTO,
    StampingProcessFeeBatchReverseAuditDTO,
    StampingProcessFeeCalcDTO,
    StampingProcessFeeDeleteDTO,
    StampingProcessFeeQuery,
    StampingProcessFeeUpdateDTO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.stamping_process_fee_vo import (
    StampingProcessFeeBatchAuditResultVO,
    StampingProcessFeeBatchDeleteResultVO,
    StampingProcessFeeCalcLogVO,
    StampingProcessFeeCalcReadyVO,
    StampingProcessFeeCalcResultVO,
    StampingProcessFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_STAMPING_PROCESS_FEE_CALC,
    AsyncTaskService,
)
from app.services.stamping.process_fee import (
    StampingProcessFeeCalcOrchestrator,
)
from app.services.stamping.stamping_process_fee_export_service import (
    StampingProcessFeeExportService,
)
from app.services.stamping.stamping_process_fee_service import (
    StampingProcessFeeService,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/stamping/process-fees", tags=["冲压加工费 API"])

_service = StampingProcessFeeService()
_calc_orchestrator = StampingProcessFeeCalcOrchestrator()
_export_service = StampingProcessFeeExportService()
_async_task_service = AsyncTaskService()


@router.get(
    "/filters/years",
    response_model=ApiResponse[list[int]],
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[int]]:
    years = _service.list_years(db)
    return ApiResponse.ok(data=years)


@router.get(
    "/filters/locations",
    response_model=ApiResponse[list[str]],
)
def list_locations(
    year: int | None = Query(None, description="年度"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    locations = _service.list_locations(db, year=year)
    return ApiResponse.ok(data=locations)


@router.get(
    "/filters/suppliers",
    response_model=ApiResponse[list[str]],
)
def list_suppliers(
    year: int | None = Query(None, description="年度"),
    location: str | None = Query(None, description="基地"),
    vehicle_model: str | None = Query(None, description="项目"),
    version: str | None = Query(None, description="版本"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    suppliers = _service.list_suppliers(
        db,
        year=year,
        location=location,
        vehicle_model=(vehicle_model or "").strip() or None,
        version=(version or "").strip() or None,
    )
    return ApiResponse.ok(data=suppliers)


@router.get(
    "/filters/vehicle-models",
    response_model=ApiResponse[list[str]],
)
def list_vehicle_models(
    year: int | None = Query(None, description="年度"),
    location: str | None = Query(None, description="基地"),
    stamping_supplier: str | None = Query(None, description="冲压工厂"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    models = _service.list_vehicle_models(
        db,
        year=year,
        location=location,
        stamping_supplier=stamping_supplier,
    )
    return ApiResponse.ok(data=models)


@router.get(
    "/filters/versions",
    response_model=ApiResponse[list[str]],
)
def list_versions(
    year: int | None = Query(None, description="年度"),
    location: str | None = Query(None, description="基地"),
    stamping_supplier: str | None = Query(None, description="冲压工厂"),
    vehicle_model: str | None = Query(None, description="项目"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    versions = _service.list_versions(
        db,
        year=year,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
    )
    return ApiResponse.ok(data=versions)


@router.get(
    "/calc/ready",
    response_model=ApiResponse[StampingProcessFeeCalcReadyVO],
)
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    version: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_VIEW)),
) -> ApiResponse[StampingProcessFeeCalcReadyVO]:
    data = _calc_orchestrator.get_calc_ready(
        db,
        year=year,
        location=location or None,
        vehicle_model=vehicle_model or None,
        version=version or None,
    )
    return ApiResponse.ok(data=data)


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[StampingProcessFeeCalcLogVO]],
)
def list_calc_logs(
    year: int | None = Query(None),
    location: str | None = Query(None),
    stamping_supplier: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_VIEW)),
) -> ApiResponse[PageResult[StampingProcessFeeCalcLogVO]]:
    rows, total = _calc_orchestrator.list_calc_logs(
        db,
        year=year,
        location=location,
        stamping_supplier=stamping_supplier,
        page=page,
        size=size,
    )
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=page,
        page_size=size,
        message=f"查询到 {total} 条计算历史",
    )


@router.get(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[StampingProcessFeeCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_VIEW)),
) -> ApiResponse[StampingProcessFeeCalcLogVO]:
    record = _calc_orchestrator.get_calc_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs",
    response_model=ApiResponse[DeletedCountVO],
)
def delete_all_calc_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _calc_orchestrator.delete_all_calc_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_DELETE)),
) -> ApiResponse[None]:
    _calc_orchestrator.delete_calc_log(db, log_id)
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_STAMPING_PROCESS_FEE_CALC)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = StampingProcessFeeCalcResultVO.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.post(
    "/calc",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
)
def calculate(
    dto: StampingProcessFeeCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """提交异步计算；立即返回 task_id，前端轮询进度。"""
    accepted = _calc_orchestrator.start_calc(db, dto, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台计算",
    )


@router.get(
    "",
    response_model=ApiResponse[PageResult[StampingProcessFeeVO]],
)
def list_fees(
    query: StampingProcessFeeQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_VIEW)),
) -> ApiResponse[PageResult[StampingProcessFeeVO]]:
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
    location: str | None = Query(None, description="基地"),
    stamping_supplier: str | None = Query(None, description="冲压工厂"),
    vehicle_model: str | None = Query(None, description="项目"),
    version: str | None = Query(None, description="版本"),
    part_number: str | None = Query(None, description="零件号"),
    audit_status: str | None = Query(None, description="审核状态"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出冲压加工费 Excel。"""
    content, filename = _export_service.export(
        db,
        year=year,
        location=location.strip() if location else None,
        stamping_supplier=stamping_supplier.strip() if stamping_supplier else None,
        vehicle_model=vehicle_model.strip() if vehicle_model else None,
        version=version.strip() if version else None,
        part_number=part_number.strip() if part_number else None,
        audit_status=audit_status.strip() if audit_status else None,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/{fee_id}",
    response_model=ApiResponse[StampingProcessFeeVO],
)
def get_fee(
    fee_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_VIEW)),
) -> ApiResponse[StampingProcessFeeVO]:
    row = _service.get_by_id(db, fee_id)
    return ApiResponse.ok(data=row)


@router.patch(
    "/{fee_id}",
    response_model=ApiResponse[StampingProcessFeeVO],
)
def update_other_fee(
    fee_id: int,
    dto: StampingProcessFeeUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_UPDATE)),
) -> ApiResponse[StampingProcessFeeVO]:
    row = _service.update_other_fee(db, fee_id, dto, current_user=current_user)
    return ApiResponse.updated(data=row, message="加工费已保存")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[StampingProcessFeeBatchDeleteResultVO],
)
def batch_delete_fees(
    dto: StampingProcessFeeDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_DELETE)),
) -> ApiResponse[StampingProcessFeeBatchDeleteResultVO]:
    result = _service.batch_delete(db, dto)
    message = f"已删除 {result.deleted_count} 条"
    if result.skipped_approved_count:
        message += f"，跳过已审核 {result.skipped_approved_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-approve",
    response_model=ApiResponse[StampingProcessFeeBatchAuditResultVO],
)
def batch_approve_fees(
    dto: StampingProcessFeeBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_APPROVE)),
) -> ApiResponse[StampingProcessFeeBatchAuditResultVO]:
    result = _service.batch_approve(db, dto, current_user=current_user)
    message = f"已审核通过 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[StampingProcessFeeBatchAuditResultVO],
)
def batch_reverse_audit_fees(
    dto: StampingProcessFeeBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_REVERSE)),
) -> ApiResponse[StampingProcessFeeBatchAuditResultVO]:
    result = _service.batch_reverse_audit(db, dto, current_user=current_user)
    message = f"已反审核 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)
