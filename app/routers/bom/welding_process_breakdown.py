"""
BOM 焊接工艺拆解路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.common.audit import display_name
from app.common.permissions.codes import Perm
from app.database import DatabaseConfig, get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownBatchApproveDTO,
    BomWeldingProcessBreakdownBatchDeleteDTO,
    BomWeldingProcessBreakdownBatchReverseAuditDTO,
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownLineUpdateDTO,
    BomWeldingProcessBreakdownQuery,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownBatchAuditResultVO,
    BomWeldingProcessBreakdownBatchDeleteResultVO,
    BomWeldingProcessBreakdownGenerateLogVO,
    BomWeldingProcessBreakdownGeneratePrepStatsVO,
    BomWeldingProcessBreakdownGenerateResultVO,
    BomWeldingProcessBreakdownLineVO,
    BomWeldingProcessBreakdownNodeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
    AsyncTaskService,
)
from app.services.bom.welding_process_breakdown import (
    BomWeldingProcessBreakdownService,
)
from app.services.bom.welding_process_breakdown.export import (
    BomWeldingProcessBreakdownExportOrchestrator,
)
from app.services.bom.welding_process_breakdown.generate_log_service import (
    DUPLICATE_SCOPE_GENERATE_MESSAGE,
    DuplicateScopeGenerateError,
)
from app.utils.logging_config import get_logger
from app.utils.response import ApiResponse

logger = get_logger("router.bom.welding_process_breakdown")

router = APIRouter(
    prefix="/api/bom/welding-process-breakdown",
    tags=["BOM 焊接工艺拆解 API"],
)

_service = BomWeldingProcessBreakdownService()
_export_orchestrator = BomWeldingProcessBreakdownExportOrchestrator()
_async_task_service = AsyncTaskService()


def _process_generate_in_background(
    task_id: str,
    log_id: int,
    calc_batch_id: str,
    location: str,
    vehicle_model: str,
    bom_version: str,
    customer_name: str | None,
    started_at_iso: str | None,
    current_user: UserVO,
) -> None:
    """后台线程执行拆解；独立 Session。"""
    from datetime import datetime

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    def on_progress(progress: int, msg: str) -> None:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=progress,
            message=msg,
        )

    started_at = None
    if started_at_iso:
        try:
            started_at = datetime.fromisoformat(started_at_iso)
        except ValueError:
            started_at = None

    try:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=1,
            message="后台开始拆解...",
        )
        dto = BomWeldingProcessBreakdownGenerateDTO(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name=customer_name,
        )
        result, error = _service.generate_from_bom(
            db,
            dto,
            current_user,
            progress_callback=on_progress,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            started_at=started_at,
        )
        if error or result is None:
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message=error or "拆解失败",
                result=(
                    BomWeldingProcessBreakdownGenerateResultVO(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                        status="failed",
                        message=error or "拆解失败",
                        calc_batch_id=calc_batch_id,
                        log_id=log_id,
                        detail_text=error or "",
                    ).model_dump()
                ),
            )
            return

        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_COMPLETED,
            progress=100,
            message=result.message,
            result=result.model_dump(),
        )
    except Exception as error:
        logger.exception("焊接工艺拆解异常: task_id=%s log_id=%s", task_id, log_id)
        try:
            _service.mark_generate_log_failed(
                db,
                log_id=log_id,
                message=str(error),
                detail_text=f"拆解异常: {error}",
            )
        except Exception:
            logger.exception("释放拆解锁失败: log_id=%s", log_id)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=f"拆解异常: {error}",
        )
    finally:
        db.close()


@router.get(
    "/paginate",
    response_model=ApiResponse[PageResult[BomWeldingProcessBreakdownNodeVO]],
)
def paginate(
    query: BomWeldingProcessBreakdownQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW)),
) -> ApiResponse[PageResult[BomWeldingProcessBreakdownNodeVO]]:
    """分页查询焊接工艺拆解主表（明细请用 GET /nodes/{id}）。"""
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
def export_l0_excel(
    location: str | None = Query(None, description="采购基地"),
    customer_name: str | None = Query(None, description="顾客名称"),
    vehicle_model: str | None = Query(None, description="项目/车型"),
    bom_version: str | None = Query(None, description="材料清单版本"),
    part_number: str | None = Query(None, description="零件号（模糊）"),
    process_line_count_eq: int | None = Query(
        None, description="工艺明细行数精确匹配；传 0 仅导出无工艺 L0"
    ),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_EXPORT)
    ),
) -> StreamingResponse:
    """
    导出 L0 供货总成工艺核对表（主表字段 merge 到明细行；不含审核信息）。
    """
    content, filename = _export_orchestrator.export(
        db,
        location=location.strip() if location else None,
        customer_name=customer_name.strip() if customer_name else None,
        vehicle_model=vehicle_model.strip() if vehicle_model else None,
        bom_version=bom_version.strip() if bom_version else None,
        part_number=part_number.strip() if part_number else None,
        process_line_count_eq=process_line_count_eq,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.get(
    "/nodes/{node_id}",
    response_model=ApiResponse[BomWeldingProcessBreakdownNodeVO],
)
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW)),
) -> ApiResponse[BomWeldingProcessBreakdownNodeVO]:
    row = _service.get_node(db, node_id)
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ApiResponse.ok(data=row)


@router.get(
    "/generate/prep-stats",
    response_model=ApiResponse[BomWeldingProcessBreakdownGeneratePrepStatsVO],
)
def get_generate_prep_stats(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_GENERATE)
    ),
) -> ApiResponse[BomWeldingProcessBreakdownGeneratePrepStatsVO]:
    """拆解前数据就绪统计。"""
    stats = _service.get_generate_prep_stats(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    return ApiResponse.ok(data=stats)


@router.get(
    "/generate/logs",
    response_model=ApiResponse[PageResult[BomWeldingProcessBreakdownGenerateLogVO]],
)
def list_generate_logs(
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW)
    ),
) -> ApiResponse[PageResult[BomWeldingProcessBreakdownGenerateLogVO]]:
    records, total = _service.list_generate_logs(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        page=page,
        size=size,
    )
    return ApiResponse.list_(
        items=records,
        total=total,
        page=page,
        page_size=size,
    )


@router.get(
    "/generate/logs/{log_id}",
    response_model=ApiResponse[BomWeldingProcessBreakdownGenerateLogVO],
)
def get_generate_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW)
    ),
) -> ApiResponse[BomWeldingProcessBreakdownGenerateLogVO]:
    record = _service.get_generate_log(db, log_id)
    if record is None:
        raise HTTPException(status_code=404, detail="拆解记录不存在")
    return ApiResponse.ok(data=record)


@router.delete(
    "/generate/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_generate_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_DELETE_LOG)
    ),
) -> ApiResponse[None]:
    try:
        deleted = _service.delete_generate_log(db, log_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="拆解记录不存在")
    return ApiResponse.deleted(message="删除成功")


@router.get(
    "/generate/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_generate_task_progress(
    task_id: str,
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW)
    ),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.get_task_snapshot(task_id)
    if (
        task is None
        or task.get("task_type") != TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE
    ):
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = (
        BomWeldingProcessBreakdownGenerateResultVO.model_validate(result_raw)
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
    "/generate",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
)
def generate_from_bom(
    dto: BomWeldingProcessBreakdownGenerateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_GENERATE)
    ),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """从 BOM 异步生成焊接工艺拆解。"""
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    bom_version = dto.bom_version.strip()
    customer_name = (dto.customer_name or "").strip() or None

    try:
        lock_log = _service.begin_generate_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            customer_name=customer_name,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
    except DuplicateScopeGenerateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error) or DUPLICATE_SCOPE_GENERATE_MESSAGE,
        ) from error

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
        message="已提交拆解队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    started_at_iso = (
        lock_log.started_at.isoformat(timespec="seconds") if lock_log.started_at else None
    )
    AsyncTaskService.submit(
        _process_generate_in_background,
        task.task_id,
        lock_log.id,
        lock_log.calc_batch_id,
        location,
        vehicle_model,
        bom_version,
        customer_name,
        started_at_iso,
        current_user,
    )
    return ApiResponse.ok(
        data=AsyncTaskAcceptedVO(task_id=task.task_id),
        message="已提交后台拆解",
    )


@router.patch(
    "/lines/{line_id}",
    response_model=ApiResponse[BomWeldingProcessBreakdownLineVO],
)
def update_line(
    line_id: int,
    dto: BomWeldingProcessBreakdownLineUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_UPDATE)
    ),
) -> ApiResponse[BomWeldingProcessBreakdownLineVO]:
    """修改明细（过程量/标准工艺）；map/rollup/qty_check 由服务侧重算"""
    row, error = _service.update_line(db, line_id, dto, current_user=current_user)
    if error:
        code = 404 if "不存在" in error else 400
        raise HTTPException(status_code=code, detail=error)
    return ApiResponse.updated(data=row, message="更新成功")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BomWeldingProcessBreakdownBatchDeleteResultVO],
)
def batch_delete(
    dto: BomWeldingProcessBreakdownBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_DELETE)
    ),
) -> ApiResponse[BomWeldingProcessBreakdownBatchDeleteResultVO]:
    """按基地+项目+版本批量删除（仅未审核）"""
    result, error = _service.batch_delete(
        db,
        location=dto.location,
        vehicle_model=dto.vehicle_model,
        bom_version=dto.bom_version,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return ApiResponse.ok(data=result, message=result.message if result else "删除成功")


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO],
)
def batch_approve(
    dto: BomWeldingProcessBreakdownBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_APPROVE)
    ),
) -> ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO]:
    """按基地+项目+版本批量审核"""
    result, error = _service.batch_approve(db, dto, current_user=current_user)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return ApiResponse.ok(
        data=result,
        message=f"已审核 {result.updated_count if result else 0} 条",
    )


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO],
)
def batch_reverse_audit(
    dto: BomWeldingProcessBreakdownBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_REVERSE)
    ),
) -> ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO]:
    """按基地+项目+版本批量反审核"""
    result, error = _service.batch_reverse_audit(db, dto, current_user=current_user)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return ApiResponse.ok(
        data=result,
        message=f"已反审核 {result.updated_count if result else 0} 条",
    )
