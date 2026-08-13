"""
冲压加工费路由
异步计算 + 计算日志 + 列表审核删除
"""

from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.permissions.codes import Perm
from app.database import DatabaseConfig, get_db
from app.deps.permissions import require_any_perm, require_perm
from app.exceptions.base import BusinessException
from app.schemas.common.page_result import PageResult
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
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_STAMPING_PROCESS_FEE_CALC,
    AsyncTaskService,
)
from app.services.stamping.stamping_process_fee_export_service import (
    StampingProcessFeeExportService,
)
from app.services.stamping.stamping_process_fee_service import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    DuplicateScopeCalcError,
    StampingProcessFeeService,
)
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/stamping/process-fees", tags=["冲压加工费 API"])

_service = StampingProcessFeeService()
_export_service = StampingProcessFeeExportService()
_async_task_service = AsyncTaskService()


def _process_calc_in_background(
    task_id: str,
    log_id: int,
    calc_batch_id: str,
    year: int,
    location: str,
    stamping_supplier: str,
    vehicle_model: str | None,
    version: str | None,
    current_user: UserVO,
) -> None:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    def on_progress(progress: int, msg: str) -> None:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=progress,
            message=msg,
        )

    try:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=1,
            message="后台开始计算...",
        )
        dto = StampingProcessFeeCalcDTO(
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        result = _service.calculate(
            db,
            dto,
            current_user=current_user,
            progress_callback=on_progress,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )
        if result.status == "failed":
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message=(
                    f"计算失败：成功 {result.success_count}，失败 {result.failed_count}"
                ),
                result=result.model_dump(),
            )
        else:
            label = {"success": "成功", "partial": "部分成功"}.get(
                result.status, result.status
            )
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_COMPLETED,
                progress=100,
                message=(
                    f"计算{label}：成功 {result.success_count}，"
                    f"失败 {result.failed_count}，零价 {result.zero_fee_count}"
                ),
                result=result.model_dump(),
            )
    except Exception as error:
        try:
            _service.mark_log_failed(
                db,
                log_id=log_id,
                detail_text=f"计算失败: {error}",
            )
        except Exception:
            pass
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=str(error),
        )
    finally:
        db.close()


@router.get(
    "/filters/years",
    response_model=ApiResponse[List[int]],
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[List[int]]:
    years = _service.list_years(db)
    return ApiResponse.ok(data=years)


@router.get(
    "/filters/locations",
    response_model=ApiResponse[List[str]],
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
) -> ApiResponse[List[str]]:
    locations = _service.list_locations(db, year=year)
    return ApiResponse.ok(data=locations)


@router.get(
    "/filters/suppliers",
    response_model=ApiResponse[List[str]],
)
def list_suppliers(
    year: int | None = Query(None, description="年度"),
    location: str | None = Query(None, description="基地"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PROCESS_FEE_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[List[str]]:
    suppliers = _service.list_suppliers(db, year=year, location=location)
    return ApiResponse.ok(data=suppliers)


@router.get(
    "/calc/ready",
    response_model=ApiResponse[StampingProcessFeeCalcReadyVO],
)
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    location: str | None = Query(None),
    stamping_supplier: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    version: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_VIEW)),
) -> ApiResponse[StampingProcessFeeCalcReadyVO]:
    data = _service.get_calc_ready(
        db,
        year=year,
        location=location or None,
        stamping_supplier=stamping_supplier or None,
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
    rows, total = _service.list_calc_logs(
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
    record = _service.get_calc_log(db, log_id)
    if not record:
        raise HTTPException(status_code=404, detail="计算日志不存在")
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_DELETE)),
) -> ApiResponse[None]:
    try:
        deleted = _service.delete_calc_log(db, log_id)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="计算日志不存在")
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_STAMPING_PROCESS_FEE_CALC:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = (
        StampingProcessFeeCalcResultVO.model_validate(result_raw)
        if result_raw
        else None
    )
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
    try:
        lock_log = _service.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
    except DuplicateScopeCalcError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error) or DUPLICATE_SCOPE_CALC_MESSAGE,
        ) from error

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_STAMPING_PROCESS_FEE_CALC,
        message="已提交计算队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    AsyncTaskService.submit(
        _process_calc_in_background,
        task.task_id,
        lock_log.id,
        lock_log.calc_batch_id,
        dto.year,
        dto.location,
        dto.stamping_supplier,
        dto.vehicle_model,
        dto.version,
        current_user,
    )
    return ApiResponse.ok(
        data=AsyncTaskAcceptedVO(task_id=task.task_id),
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
    vehicle_model: str | None = Query(None, description="车型"),
    version: str | None = Query(None, description="版本"),
    part_number: str | None = Query(None, description="零件号"),
    audit_status: str | None = Query(None, description="审核状态"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出冲压加工费 Excel。"""
    if not any([year, location, stamping_supplier, vehicle_model, version, part_number, audit_status]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一个筛选条件后再导出",
        )

    content, filename = _export_service.export(
        db,
        year=year,
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
    if not row:
        raise HTTPException(status_code=404, detail="加工费记录不存在")
    return ApiResponse.ok(data=row)


@router.patch(
    "/{fee_id}",
    response_model=ApiResponse[StampingProcessFeeVO],
)
def update_manual_price(
    fee_id: int,
    dto: StampingProcessFeeUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PROCESS_FEE_UPDATE)),
) -> ApiResponse[StampingProcessFeeVO]:
    row = _service.update_manual_price(db, fee_id, dto, current_user=current_user)
    return ApiResponse.updated(data=row, message="手工调整已保存")


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
