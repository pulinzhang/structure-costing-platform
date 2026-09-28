"""
BOM 焊接工艺拆解路由
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownBatchApproveDTO,
    BomWeldingProcessBreakdownBatchDeleteDTO,
    BomWeldingProcessBreakdownBatchReverseAuditDTO,
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownLineUpdateDTO,
    BomWeldingProcessBreakdownNodeLinesUpdateDTO,
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
from app.services.async_task.service import (
    STATUS_PENDING,
    TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
    AsyncTaskService,
)
from app.services.bom.welding_process_breakdown.export.orchestrator import (
    BomWeldingProcessBreakdownExportOrchestrator,
)
from app.services.bom.welding_process_breakdown.service import BomWeldingProcessBreakdownService
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/bom/welding-process-breakdown",
    tags=["BOM 焊接工艺拆解 API"],
)

_service = BomWeldingProcessBreakdownService()
_export_orchestrator = BomWeldingProcessBreakdownExportOrchestrator()
_async_task_service = AsyncTaskService()


@router.get(
    "/paginate",
    response_model=ApiResponse[PageResult[BomWeldingProcessBreakdownNodeVO]],
    summary="分页查询焊接工艺拆解主表",
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


@router.get("/export", summary="导出 L0 供货总成工艺核对表")
def export_l0_excel(
    location: str | None = Query(None, description="采购基地"),
    customer_name: str | None = Query(None, description="顾客名称"),
    vehicle_model: str | None = Query(None, description="项目"),
    bom_version: str | None = Query(None, description="材料清单版本"),
    part_number: str | None = Query(None, description="零件号（模糊）"),
    process_line_count_eq: int | None = Query(
        None, description="工艺明细行数精确匹配；传 0 仅导出无工艺 L0"
    ),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_EXPORT)),
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
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/nodes/{node_id:int}",
    response_model=ApiResponse[BomWeldingProcessBreakdownNodeVO],
    summary="查看焊接工艺拆解节点",
)
def get_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW)),
) -> ApiResponse[BomWeldingProcessBreakdownNodeVO]:
    row = _service.get_node(db, node_id)
    return ApiResponse.ok(data=row)


@router.get(
    "/generate/prep-stats",
    response_model=ApiResponse[BomWeldingProcessBreakdownGeneratePrepStatsVO],
    summary="拆解前数据就绪统计",
)
def get_generate_prep_stats(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_GENERATE)),
) -> ApiResponse[BomWeldingProcessBreakdownGeneratePrepStatsVO]:
    """拆解前数据就绪统计。"""
    stats = _service.get_generate_prep_stats(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    return ApiResponse.ok(data=stats)


# 生成页可读：有「从BOM生成」或「列表查询」均可看日志 / 任务进度
_generate_read = require_any_perm(
    Perm.BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
    Perm.BOM_WELDING_PROCESS_BREAKDOWN_VIEW,
)


@router.get(
    "/generate/logs",
    response_model=ApiResponse[PageResult[BomWeldingProcessBreakdownGenerateLogVO]],
    summary="分页查询焊接工艺拆解生成日志",
)
def list_generate_logs(
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_generate_read),
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
    "/generate/logs/{log_id:int}",
    response_model=ApiResponse[BomWeldingProcessBreakdownGenerateLogVO],
    summary="查看焊接工艺拆解生成日志",
)
def get_generate_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_generate_read),
) -> ApiResponse[BomWeldingProcessBreakdownGenerateLogVO]:
    record = _service.get_generate_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.delete(
    "/generate/logs",
    response_model=ApiResponse[DeletedCountVO],
    summary="删除全部焊接工艺拆解生成日志",
)
def delete_all_generate_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_DELETE_LOG)),
) -> ApiResponse[DeletedCountVO]:
    result = _service.delete_all_generate_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete(
    "/generate/logs/{log_id:int}",
    response_model=ApiResponse[None],
    summary="删除一条焊接工艺拆解生成日志",
)
def delete_generate_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_DELETE_LOG)),
) -> ApiResponse[None]:
    _service.delete_generate_log(db, log_id)
    return ApiResponse.deleted(message="删除成功")


@router.get(
    "/generate/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
    summary="查询焊接工艺拆解生成进度",
)
def get_generate_task_progress(
    task_id: str,
    current_user: UserVO = Depends(_generate_read),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(
        task_id, TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE
    )

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
    summary="从 BOM 异步生成焊接工艺拆解",
)
def generate_from_bom(
    dto: BomWeldingProcessBreakdownGenerateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_GENERATE)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """从 BOM 异步生成焊接工艺拆解。"""
    accepted = _service.start_generate(db, dto, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台拆解",
    )


@router.patch(
    "/lines/{line_id:int}",
    response_model=ApiResponse[BomWeldingProcessBreakdownLineVO],
    summary="修改焊接工艺明细",
)
def update_line(
    line_id: int,
    dto: BomWeldingProcessBreakdownLineUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_SAVE_LINES)),
) -> ApiResponse[BomWeldingProcessBreakdownLineVO]:
    """修改明细（过程量/标准工艺）；map/rollup/qty_check 由服务侧重算"""
    row = _service.update_line(db, line_id, dto, current_user=current_user)
    return ApiResponse.updated(data=row, message="更新成功")


@router.patch(
    "/nodes/{node_id:int}/lines",
    response_model=ApiResponse[BomWeldingProcessBreakdownNodeVO],
    summary="一次保存节点下全部工艺明细",
)
def update_node_lines(
    node_id: int,
    dto: BomWeldingProcessBreakdownNodeLinesUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_SAVE_LINES)),
) -> ApiResponse[BomWeldingProcessBreakdownNodeVO]:
    """一次保存节点下全部工艺明细"""
    row = _service.update_node_lines(db, node_id, dto, current_user=current_user)
    return ApiResponse.updated(data=row, message="全部工艺已保存")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BomWeldingProcessBreakdownBatchDeleteResultVO],
    summary="按基地+项目+版本批量删除",
)
def batch_delete(
    dto: BomWeldingProcessBreakdownBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_DELETE)),
) -> ApiResponse[BomWeldingProcessBreakdownBatchDeleteResultVO]:
    """按基地+项目+版本批量删除（仅未审核）"""
    result = _service.batch_delete(
        db,
        location=dto.location,
        vehicle_model=dto.vehicle_model,
        bom_version=dto.bom_version,
    )
    return ApiResponse.ok(data=result, message=result.message if result else "删除成功")


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO],
    summary="按基地+项目+版本批量审核",
)
def batch_approve(
    dto: BomWeldingProcessBreakdownBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_APPROVE)),
) -> ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO]:
    """按基地+项目+版本批量审核"""
    result = _service.batch_approve(db, dto, current_user=current_user)
    return ApiResponse.ok(
        data=result,
        message=f"已审核 {result.updated_count if result else 0} 条",
    )


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO],
    summary="按基地+项目+版本批量反审核",
)
def batch_reverse_audit(
    dto: BomWeldingProcessBreakdownBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_PROCESS_BREAKDOWN_REVERSE)),
) -> ApiResponse[BomWeldingProcessBreakdownBatchAuditResultVO]:
    """按基地+项目+版本批量反审核"""
    result = _service.batch_reverse_audit(db, dto, current_user=current_user)
    return ApiResponse.ok(
        data=result,
        message=f"已反审核 {result.updated_count if result else 0} 条",
    )
