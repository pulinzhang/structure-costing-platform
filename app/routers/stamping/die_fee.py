"""冲压年度模具费路由。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.common.vehicle_model import normalize_vehicle_model
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common import DeletedCountVO, PageResult
from app.schemas.dto.stamping_die_fee_dto import (
    StampingDieFeeBatchApproveDTO,
    StampingDieFeeBatchReverseAuditDTO,
    StampingDieFeeCalcDTO,
    StampingDieFeeDeleteDTO,
    StampingDieFeeQuery,
    StampingDieFeeUpdateDTO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.stamping_die_fee_vo import (
    StampingDieFeeBatchAuditResultVO,
    StampingDieFeeBatchDeleteResultVO,
    StampingDieFeeCalcLogVO,
    StampingDieFeeCalcReadyVO,
    StampingDieFeeCalcResultVO,
    StampingDieFeeFilterVO,
    StampingDieFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_STAMPING_DIE_FEE_CALC,
    AsyncTaskService,
)
from app.services.stamping.die_fee.calc.orchestrator import StampingDieFeeCalcOrchestrator
from app.services.stamping.die_fee.die_fee_service import StampingDieFeeService
from app.services.stamping.die_fee.export_service import StampingDieFeeExportService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/stamping/die-fees", tags=["冲压模具费 API"])

_service = StampingDieFeeService()
_calc_orchestrator = StampingDieFeeCalcOrchestrator()
_export_service = StampingDieFeeExportService()
_async_task_service = AsyncTaskService()


@router.get("/filters", response_model=ApiResponse[StampingDieFeeFilterVO])
def list_filters(
    location: str | None = Query(None),
    year: int | None = Query(None, ge=2000, le=2100),
    vehicle_model: str | None = Query(None),
    stamping_supplier: str | None = Query(None),
    for_calc: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.STAMPING_DIE_FEE_VIEW, Perm.STAMPING_DIE_FEE_CALC_VIEW)
    ),
) -> ApiResponse[StampingDieFeeFilterVO]:
    location_value = location.strip() if location else None
    vehicle_value = (
        normalize_vehicle_model(vehicle_model) if (vehicle_model or "").strip() else None
    )
    supplier_value = stamping_supplier.strip() if stamping_supplier else None
    return ApiResponse.ok(
        data=_service.list_filters(
            db,
            location=location_value,
            year=year,
            vehicle_model=vehicle_value,
            stamping_supplier=supplier_value,
            for_calc=for_calc,
        )
    )


@router.get("/calc/ready", response_model=ApiResponse[StampingDieFeeCalcReadyVO])
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    version: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_VIEW)),
) -> ApiResponse[StampingDieFeeCalcReadyVO]:
    data = _calc_orchestrator.get_calc_ready(
        db,
        year=year,
        location=(location or "").strip() or None,
        vehicle_model=normalize_vehicle_model(vehicle_model)
        if (vehicle_model or "").strip()
        else None,
        version=(version or "").strip() or None,
    )
    return ApiResponse.ok(data=data)


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[StampingDieFeeCalcLogVO]],
)
def list_calc_logs(
    year: int | None = Query(None),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    stamping_supplier: str | None = Query(None),
    version: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_VIEW)),
) -> ApiResponse[PageResult[StampingDieFeeCalcLogVO]]:
    rows, total = _calc_orchestrator.list_calc_logs(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        stamping_supplier=(stamping_supplier or "").strip() or None,
        version=(version or "").strip() or None,
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
    response_model=ApiResponse[StampingDieFeeCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_VIEW)),
) -> ApiResponse[StampingDieFeeCalcLogVO]:
    return ApiResponse.ok(data=_calc_orchestrator.get_calc_log(db, log_id))


@router.delete(
    "/calc/logs",
    response_model=ApiResponse[DeletedCountVO],
)
def delete_all_calc_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _calc_orchestrator.delete_all_calc_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete("/calc/logs/{log_id}", response_model=ApiResponse[None])
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_DELETE)),
) -> ApiResponse[None]:
    _calc_orchestrator.delete_calc_log(db, log_id)
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/progress/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_STAMPING_DIE_FEE_CALC)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = StampingDieFeeCalcResultVO.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.post("/calc", response_model=ApiResponse[AsyncTaskAcceptedVO])
def calculate(
    dto: StampingDieFeeCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    accepted = _calc_orchestrator.start_calc(db, dto, current_user=current_user)
    return ApiResponse.ok(data=accepted, message="已提交后台计算")


@router.get("", response_model=ApiResponse[PageResult[StampingDieFeeVO]])
def list_fees(
    query: StampingDieFeeQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_VIEW)),
) -> ApiResponse[PageResult[StampingDieFeeVO]]:
    rows, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/export")
def export_download(
    year: int = Query(..., ge=2000, le=2100),
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    stamping_supplier: str | None = Query(None),
    version: str | None = Query(None),
    part_number: str | None = Query(None),
    audit_status: str | None = Query(None),
    only_zero: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export(
        db,
        year=year,
        location=location.strip(),
        vehicle_model=vehicle_model.strip(),
        stamping_supplier=stamping_supplier.strip() if stamping_supplier else None,
        version=version.strip() if version else None,
        part_number=part_number.strip() if part_number else None,
        audit_status=audit_status.strip() if audit_status else None,
        only_zero=only_zero,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.delete("/scope", response_model=ApiResponse[StampingDieFeeBatchDeleteResultVO])
def delete_scope(
    year: int = Query(..., ge=2000, le=2100),
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_DELETE)),
) -> ApiResponse[StampingDieFeeBatchDeleteResultVO]:
    dto = StampingDieFeeDeleteDTO(
        year=year,
        location=location,
        vehicle_model=vehicle_model,
    )
    result = _service.delete_scope(db, dto)
    message = f"已删除 {result.deleted_count} 条"
    if result.skipped_approved_count:
        message += f"，跳过已审核 {result.skipped_approved_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-approve",
    response_model=ApiResponse[StampingDieFeeBatchAuditResultVO],
)
def batch_approve(
    dto: StampingDieFeeBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_APPROVE)),
) -> ApiResponse[StampingDieFeeBatchAuditResultVO]:
    result = _service.batch_approve(db, dto, current_user=current_user)
    message = f"已审核通过 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[StampingDieFeeBatchAuditResultVO],
)
def batch_reverse_audit(
    dto: StampingDieFeeBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_REVERSE)),
) -> ApiResponse[StampingDieFeeBatchAuditResultVO]:
    result = _service.batch_reverse_audit(db, dto, current_user=current_user)
    message = f"已反审核 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.get("/{fee_id}", response_model=ApiResponse[StampingDieFeeVO])
def get_fee(
    fee_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_VIEW)),
) -> ApiResponse[StampingDieFeeVO]:
    return ApiResponse.ok(data=_service.get_by_id(db, fee_id))


@router.put("/{fee_id}", response_model=ApiResponse[StampingDieFeeVO])
def update_adjustment(
    fee_id: int,
    dto: StampingDieFeeUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_UPDATE)),
) -> ApiResponse[StampingDieFeeVO]:
    row = _service.update_adjustment(db, fee_id, dto, current_user=current_user)
    return ApiResponse.updated(data=row, message="调整金额已保存")


@router.delete("/{fee_id}", response_model=ApiResponse[None])
def delete_fee(
    fee_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_FEE_DELETE)),
) -> ApiResponse[None]:
    _service.delete_one(db, fee_id)
    return ApiResponse.deleted(message="删除成功")
