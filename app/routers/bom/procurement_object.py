"""采购对象列表路由。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
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
    BomProcurementObjectSupplierChoiceQuery,
    BomProcurementObjectSupplierDTO,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectBatchAuditResultVO,
    BomProcurementObjectBatchDeleteResultVO,
    BomProcurementObjectGenerateLogVO,
    BomProcurementObjectGenerateResultVO,
    BomProcurementObjectListVO,
    BomProcurementObjectPrepStatsVO,
    BomProcurementObjectSupplierUploadResultVO,
    BomProcurementObjectVO,
)
from app.schemas.vo.supplier_vo import SupplierChoiceVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.export.service import (
    BomProcurementObjectExportService,
)
from app.services.bom.procurement_object.service import BomProcurementObjectService
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/bom/procurement-objects",
    tags=["BOM 采购对象列表 API"],
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
    summary="查询采购对象生成前统计",
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
    summary="生成采购对象",
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
        else "已生成（检测未通过，可继续确认与审核）"
    )
    return ApiResponse.ok(data=result, message=message)


@router.get(
    "/generate/logs",
    response_model=ApiResponse[PageResult[BomProcurementObjectGenerateLogVO]],
    summary="分页查询采购对象生成日志",
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
    "/generate/logs/{log_id:int}",
    response_model=ApiResponse[BomProcurementObjectGenerateLogVO],
    summary="查看采购对象生成日志",
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
    summary="查询采购对象汇总",
)
def get_summary(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str | None = Query(None),
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
    "/supplier-choices",
    response_model=ApiResponse[PageResult[SupplierChoiceVO]],
    summary="搜索采购对象可选供应商",
)
def search_supplier_choices(
    query: BomProcurementObjectSupplierChoiceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW)),
) -> ApiResponse[PageResult[SupplierChoiceVO]]:
    items, total = _service.search_supplier_choices(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get("/supplier-template", summary="下载采购对象供应商导入模板")
def download_supplier_template(
    location: str = Query(..., min_length=1),
    vehicle_model: str = Query(..., min_length=1),
    bom_version: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_SUPPLIER_UPLOAD_VIEW)),
) -> StreamingResponse:
    content, filename = _service.build_supplier_template(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    encoded = quote(filename)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.post(
    "/supplier-upload",
    response_model=ApiResponse[BomProcurementObjectSupplierUploadResultVO],
    summary="同步导入采购对象供应商",
)
async def upload_suppliers(
    location: str = Form(..., min_length=1),
    vehicle_model: str = Form(..., min_length=1),
    bom_version: str = Form(..., min_length=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_perm(Perm.BOM_PROCUREMENT_OBJECT_SUPPLIER_UPLOAD_UPLOAD)
    ),
) -> ApiResponse[BomProcurementObjectSupplierUploadResultVO]:
    content = await file.read()
    result = _service.upload_suppliers(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        filename=file.filename or "upload.xlsx",
        file_content=content,
        current_user=current_user,
    )
    message = (
        f"已更新 {result.updated_count} 条，清空 {result.cleared_count} 条，"
        f"未变 {result.unchanged_count} 条"
    )
    if result.skipped_count:
        message += f"；跳过 {result.skipped_count} 条"
        if result.skipped_details:
            message += "：" + "；".join(result.skipped_details)
    return ApiResponse.ok(data=result, message=message)


@router.get(
    "",
    response_model=ApiResponse[PageResult[BomProcurementObjectVO]],
    summary="分页查询采购对象",
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


@router.get("/export", summary="按筛选导出采购对象")
def export_excel(
    query: BomProcurementObjectQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export_excel(db, query, current_user)
    encoded = quote(filename)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get(
    "/items/{object_id:int}",
    response_model=ApiResponse[BomProcurementObjectVO],
    summary="查看采购对象",
)
def get_item(
    object_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_VIEW)),
) -> ApiResponse[BomProcurementObjectVO]:
    return ApiResponse.ok(data=_service.get_by_id(db, object_id))


@router.patch(
    "/items/{object_id:int}/confirm",
    response_model=ApiResponse[BomProcurementObjectVO],
    summary="确认采购对象",
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


@router.patch(
    "/items/{object_id:int}/supplier",
    response_model=ApiResponse[BomProcurementObjectVO],
    summary="修改采购对象供应商",
)
def update_item_supplier(
    object_id: int,
    body: BomProcurementObjectSupplierDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_UPDATE)),
) -> ApiResponse[BomProcurementObjectVO]:
    return ApiResponse.updated(
        data=_service.update_supplier(db, object_id, body, current_user=current_user),
        message="供应商已保存",
    )


@router.post(
    "/batch-approve",
    response_model=ApiResponse[BomProcurementObjectBatchAuditResultVO],
    summary="批量审核通过采购对象",
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
    summary="批量反审核采购对象",
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
    summary="批量删除采购对象",
)
def batch_delete(
    body: BomProcurementObjectBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_PROCUREMENT_OBJECT_LIST_DELETE)),
) -> ApiResponse[BomProcurementObjectBatchDeleteResultVO]:
    result = _service.batch_delete(db, body, current_user=current_user)
    if result.skipped_approved_count:
        message = (
            f"已删除 {result.deleted_count} 条，" f"跳过已审 {result.skipped_approved_count} 条"
        )
    else:
        message = f"已删除采购对象列表（{result.deleted_count} 条）"
    return ApiResponse.ok(data=result, message=message)
