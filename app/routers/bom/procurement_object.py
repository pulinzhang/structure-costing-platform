"""采购对象清单路由。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectBatchApproveDTO,
    BomProcurementObjectBatchDeleteDTO,
    BomProcurementObjectBatchReverseAuditDTO,
    BomProcurementObjectConfirmDTO,
    BomProcurementObjectGenerateDTO,
    BomProcurementObjectGenerateLogQuery,
    BomProcurementObjectPrepQuery,
    BomProcurementObjectQuery,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectBatchAuditResultVO,
    BomProcurementObjectBatchDeleteResultVO,
    BomProcurementObjectGenerateLogVO,
    BomProcurementObjectGenerateResultVO,
    BomProcurementObjectListVO,
    BomProcurementObjectPrepStatsVO,
    BomProcurementObjectVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object import BomProcurementObjectService
from app.services.bom.procurement_object.export import BomProcurementObjectExportService
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/bom/procurement-objects",
    tags=["BOM 采购对象清单 API"],
)

_service = BomProcurementObjectService()
_export_service = BomProcurementObjectExportService()

_generate_or_view = require_any_perm(
    Perm.BOM_PROCUREMENT_OBJECT_GENERATE,
    Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW,
)


@router.get(
    "/generate/prep-stats",
    response_model=ApiResponse[BomProcurementObjectPrepStatsVO],
)
def prep_stats(
    query: BomProcurementObjectPrepQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_generate_or_view),
) -> ApiResponse[BomProcurementObjectPrepStatsVO]:
    return ApiResponse.ok(data=_service.prep_stats(db, query))


@router.post(
    "/generate",
    response_model=ApiResponse[BomProcurementObjectGenerateResultVO],
)
def generate(
    body: BomProcurementObjectGenerateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_GENERATE)),
) -> ApiResponse[BomProcurementObjectGenerateResultVO]:
    result = _service.generate(db, body, current_user=current_user)
    message = (
        f"已生成采购对象 {result.object_count} 条"
        if result.header.qa_passed
        else "已生成（检测未通过，禁止确认与审核）"
    )
    return ApiResponse.ok(data=result, message=message)


@router.get(
    "/generate/logs",
    response_model=ApiResponse[PageResult[BomProcurementObjectGenerateLogVO]],
)
def list_generate_logs(
    query: BomProcurementObjectGenerateLogQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_generate_or_view),
) -> ApiResponse[PageResult[BomProcurementObjectGenerateLogVO]]:
    records, total = _service.list_generate_logs(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get(
    "/generate/logs/{log_id}",
    response_model=ApiResponse[BomProcurementObjectGenerateLogVO],
)
def get_generate_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(_generate_or_view),
) -> ApiResponse[BomProcurementObjectGenerateLogVO]:
    return ApiResponse.ok(data=_service.get_generate_log(db, log_id))


@router.get(
    "/summary",
    response_model=ApiResponse[BomProcurementObjectListVO],
)
def get_summary(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW)),
) -> ApiResponse[BomProcurementObjectListVO]:
    return ApiResponse.ok(
        data=_service.get_summary(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
    )


@router.get(
    "",
    response_model=ApiResponse[PageResult[BomProcurementObjectVO]],
)
def paginate(
    query: BomProcurementObjectQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW)),
) -> ApiResponse[PageResult[BomProcurementObjectVO]]:
    items, total, filters = _service.paginate(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/export")
def export_excel(
    query: BomProcurementObjectQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export_excel(db, query)
    encoded = quote(filename)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get(
    "/items/{object_id}",
    response_model=ApiResponse[BomProcurementObjectVO],
)
def get_item(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW)),
) -> ApiResponse[BomProcurementObjectVO]:
    return ApiResponse.ok(data=_service.get_by_id(db, object_id))


@router.patch(
    "/items/{object_id}/confirm",
    response_model=ApiResponse[BomProcurementObjectVO],
)
def confirm_item(
    object_id: int,
    body: BomProcurementObjectConfirmDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_UPDATE)),
) -> ApiResponse[BomProcurementObjectVO]:
    return ApiResponse.updated(
        data=_service.confirm(db, object_id, body, current_user=current_user),
        message="确认已保存",
    )


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomProcurementObjectBatchAuditResultVO],
)
def batch_approve(
    body: BomProcurementObjectBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_APPROVE)),
) -> ApiResponse[BomProcurementObjectBatchAuditResultVO]:
    result = _service.batch_approve(db, body, current_user=current_user)
    return ApiResponse.ok(data=result, message=f"已审核 {result.updated_count} 条")


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomProcurementObjectBatchAuditResultVO],
)
def batch_reverse_audit(
    body: BomProcurementObjectBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_REVERSE)),
) -> ApiResponse[BomProcurementObjectBatchAuditResultVO]:
    result = _service.batch_reverse_audit(db, body, current_user=current_user)
    return ApiResponse.ok(data=result, message=f"已反审核 {result.updated_count} 条")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BomProcurementObjectBatchDeleteResultVO],
)
def batch_delete(
    body: BomProcurementObjectBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_DELETE)),
) -> ApiResponse[BomProcurementObjectBatchDeleteResultVO]:
    result = _service.batch_delete(db, body, current_user=current_user)
    message = f"已删除 {result.deleted_count} 条"
    if result.skipped_approved_count:
        message += f"，跳过已审 {result.skipped_approved_count} 条"
    return ApiResponse.ok(data=result, message=message)
