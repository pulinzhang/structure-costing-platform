"""
BOM 焊接费路由
异步计算 + 计算日志 + 列表审核删除
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
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeBatchApproveDTO,
    BomWeldingFeeBatchDeleteDTO,
    BomWeldingFeeBatchReverseAuditDTO,
    BomWeldingFeeCalcDTO,
    BomWeldingFeeQuery,
    BomWeldingFeeUpdateDTO,
    coerce_level_list,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.bom_welding_fee_vo import (
    BomWeldingFeeBatchAuditResultVO,
    BomWeldingFeeBatchDeleteResultVO,
    BomWeldingFeeCalcLogVO,
    BomWeldingFeeCalcReadyVO,
    BomWeldingFeeCalcResultVO,
    BomWeldingFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_PENDING,
    TASK_TYPE_BOM_WELDING_FEE_CALC,
    AsyncTaskService,
)
from app.services.bom.welding_fee.calc.orchestrator.orchestrator import (
    BomWeldingFeeCalcOrchestrator,
)
from app.services.bom.welding_fee.export.service import BomWeldingFeeExportService
from app.services.bom.welding_fee.service import BomWeldingFeeService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom/welding-fees", tags=["BOM 焊接费 API"])

_service = BomWeldingFeeService()
_calc_orchestrator = BomWeldingFeeCalcOrchestrator()
_export_service = BomWeldingFeeExportService()
_async_task_service = AsyncTaskService()


@router.get(
    "/filters/years",
    response_model=ApiResponse[list[int]],
    summary="获取焊接费年份列表",
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.BOM_WELDING_FEE_LIST_VIEW,
            Perm.BOM_WELDING_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[int]]:
    years = _service.list_years(db)
    return ApiResponse.ok(data=years)


@router.get(
    "/filters/locations",
    response_model=ApiResponse[list[str]],
    summary="获取焊接费基地列表",
)
def list_locations(
    year: int | None = Query(None, description="年度"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.BOM_WELDING_FEE_LIST_VIEW,
            Perm.BOM_WELDING_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    locations = _service.list_locations(db, year=year)
    return ApiResponse.ok(data=locations)


@router.get(
    "/filters/vehicle-models",
    response_model=ApiResponse[list[str]],
    summary="获取焊接费项目列表",
)
def list_vehicle_models(
    year: int | None = Query(None, description="年度"),
    location: str | None = Query(None, description="基地"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.BOM_WELDING_FEE_LIST_VIEW,
            Perm.BOM_WELDING_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    models = _service.list_vehicle_models(db, year=year, location=location)
    return ApiResponse.ok(data=models)


@router.get(
    "/filters/bom-versions",
    response_model=ApiResponse[list[str]],
    summary="获取焊接费清单版本列表",
)
def list_bom_versions(
    year: int | None = Query(None, description="年度"),
    location: str | None = Query(None, description="基地"),
    vehicle_model: str | None = Query(None, description="项目"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.BOM_WELDING_FEE_LIST_VIEW,
            Perm.BOM_WELDING_FEE_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    versions = _service.list_bom_versions(
        db, year=year, location=location, vehicle_model=vehicle_model
    )
    return ApiResponse.ok(data=versions)


@router.get(
    "/calc/ready",
    response_model=ApiResponse[BomWeldingFeeCalcReadyVO],
    summary="查询焊接费计算就绪状态",
)
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_VIEW)),
) -> ApiResponse[BomWeldingFeeCalcReadyVO]:
    data = _calc_orchestrator.get_calc_ready(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
    )
    return ApiResponse.ok(data=data)


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[BomWeldingFeeCalcLogVO]],
    summary="分页查询焊接费计算日志",
)
def list_calc_logs(
    year: int | None = Query(None),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_VIEW)),
) -> ApiResponse[PageResult[BomWeldingFeeCalcLogVO]]:
    rows, total = _calc_orchestrator.list_calc_logs(
        db,
        year=year,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
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
    "/calc/logs/{log_id:int}",
    response_model=ApiResponse[BomWeldingFeeCalcLogVO],
    summary="查看焊接费计算日志",
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_VIEW)),
) -> ApiResponse[BomWeldingFeeCalcLogVO]:
    record = _calc_orchestrator.get_calc_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs",
    response_model=ApiResponse[DeletedCountVO],
    summary="删除全部焊接费计算日志",
)
def delete_all_calc_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _calc_orchestrator.delete_all_calc_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete(
    "/calc/logs/{log_id:int}",
    response_model=ApiResponse[None],
    summary="删除一条焊接费计算日志",
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_DELETE)),
) -> ApiResponse[None]:
    _calc_orchestrator.delete_calc_log(db, log_id)
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
    summary="查询焊接费计算进度",
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_BOM_WELDING_FEE_CALC)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = BomWeldingFeeCalcResultVO.model_validate(result_raw) if result_raw else None
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
    summary="提交焊接费异步计算",
)
def calculate(
    dto: BomWeldingFeeCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """提交异步计算；立即返回 task_id，前端轮询进度。"""
    accepted = _calc_orchestrator.start_calc(db, dto, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台计算",
    )


@router.get(
    "",
    response_model=ApiResponse[PageResult[BomWeldingFeeVO]],
    summary="分页查询焊接费",
)
def list_fees(
    query: BomWeldingFeeQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_VIEW)),
) -> ApiResponse[PageResult[BomWeldingFeeVO]]:
    rows, total, filters = _service.list_fees(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/export-download", summary="按当前筛选条件导出焊接费 Excel")
def export_download(
    year: int | None = Query(None, ge=2000, le=2100, description="年度"),
    location: str | None = Query(None, description="基地"),
    vehicle_model: str | None = Query(None, description="项目"),
    bom_version: str | None = Query(None, description="版本"),
    part_number: str | None = Query(None, description="零件号"),
    audit_status: str | None = Query(None, description="审核状态"),
    calc_status: str | None = Query(None, description="计算状态"),
    level: int | None = Query(None, ge=0, description="树层级（单层）"),
    levels: str | None = Query(None, description="树层级，逗号分隔，如 0,1"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出焊接费 Excel（主表字段打平到工艺明细行，按 id 升序）。"""
    content, filename = _export_service.export(
        db,
        year=year,
        location=location.strip() if location else None,
        vehicle_model=vehicle_model.strip() if vehicle_model else None,
        bom_version=bom_version.strip() if bom_version else None,
        part_number=part_number.strip() if part_number else None,
        audit_status=audit_status.strip() if audit_status else None,
        calc_status=calc_status.strip() if calc_status else None,
        level=level,
        levels=coerce_level_list(levels),
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/{fee_id:int}",
    response_model=ApiResponse[BomWeldingFeeVO],
    summary="查看焊接费",
)
def get_fee(
    fee_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_VIEW)),
) -> ApiResponse[BomWeldingFeeVO]:
    row = _service.get_by_id(db, fee_id)
    return ApiResponse.ok(data=row)


@router.patch(
    "/{fee_id:int}",
    response_model=ApiResponse[BomWeldingFeeVO],
    summary="修改焊接费其他费用",
)
def update_other_fee(
    fee_id: int,
    dto: BomWeldingFeeUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_UPDATE)),
) -> ApiResponse[BomWeldingFeeVO]:
    row = _service.update_other_fee(db, fee_id, dto, current_user=current_user)
    return ApiResponse.updated(data=row, message="焊接费已保存")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BomWeldingFeeBatchDeleteResultVO],
    summary="批量删除焊接费",
)
def batch_delete_fees(
    dto: BomWeldingFeeBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_DELETE)),
) -> ApiResponse[BomWeldingFeeBatchDeleteResultVO]:
    result = _service.batch_delete(db, dto)
    message = f"已删除 {result.deleted_count} 条"
    if result.skipped_approved_count:
        message += f"，跳过已审核 {result.skipped_approved_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomWeldingFeeBatchAuditResultVO],
    summary="批量审核通过焊接费",
)
def batch_approve_fees(
    dto: BomWeldingFeeBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_APPROVE)),
) -> ApiResponse[BomWeldingFeeBatchAuditResultVO]:
    result = _service.batch_approve(db, dto, current_user=current_user)
    message = f"已审核通过 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomWeldingFeeBatchAuditResultVO],
    summary="批量反审核焊接费",
)
def batch_reverse_audit_fees(
    dto: BomWeldingFeeBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_FEE_LIST_REVERSE)),
) -> ApiResponse[BomWeldingFeeBatchAuditResultVO]:
    result = _service.batch_reverse_audit(db, dto, current_user=current_user)
    message = f"已反审核 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)
