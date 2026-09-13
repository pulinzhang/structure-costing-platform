"""
冲次单价路由
API 接口定义
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceBatchApproveDTO,
    StampingTonnagePriceBatchDeleteDTO,
    StampingTonnagePriceBatchReverseAuditDTO,
    StampingTonnagePriceCreate,
    StampingTonnagePriceQuery,
    StampingTonnagePriceUpdate,
)
from app.schemas.vo.stamping_tonnage_price_vo import (
    StampingTonnagePriceBatchAuditResultVO,
    StampingTonnagePriceBatchDeleteResultVO,
    StampingTonnagePriceBulkUpsertResponse,
    StampingTonnagePriceImportResultVO,
    StampingTonnagePriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.tonnage_price_export_service import (
    StampingTonnagePriceExportService,
)
from app.services.stamping.tonnage_price_import_service import (
    StampingTonnagePriceImportService,
)
from app.services.stamping.tonnage_price_service import StampingTonnagePriceService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/stamping/tonnage-price", tags=["冲次单价 API"])

_tonnage_price_service = StampingTonnagePriceService()
_export_service = StampingTonnagePriceExportService()
_import_service = StampingTonnagePriceImportService()


@router.get("/list", response_model=ApiResponse[list[StampingTonnagePriceResponse]])
def list_all(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
) -> ApiResponse[list[StampingTonnagePriceResponse]]:
    """获取所有冲次单价列表（按年份、吨位排序）"""
    data = _tonnage_price_service.list_all(db)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get("/by-year/{year}", response_model=ApiResponse[list[StampingTonnagePriceResponse]])
def list_by_year(
    year: int,
    location: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
) -> ApiResponse[list[StampingTonnagePriceResponse]]:
    """获取指定年份的冲次单价；传入 location 时按基地过滤"""
    if location:
        data = _tonnage_price_service.list_by_location_year(db, location, year)
    else:
        data = _tonnage_price_service.list_by_year(db, year)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get("/paginate", response_model=ApiResponse[PageResult[StampingTonnagePriceResponse]])
def paginate(
    query: StampingTonnagePriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
) -> ApiResponse[PageResult[StampingTonnagePriceResponse]]:
    """分页查询冲次单价"""
    rows, total, filters = _tonnage_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/filters/locations", response_model=ApiResponse[list[str]])
def get_locations(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.STAMPING_TONNAGE_VIEW, Perm.STAMPING_TONNAGE_UPLOAD_VIEW)
    ),
) -> ApiResponse[list[str]]:
    """获取所有基地列表"""
    data = _tonnage_price_service.get_locations(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/years", response_model=ApiResponse[list[int]])
def get_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
) -> ApiResponse[list[int]]:
    """获取所有年份列表"""
    data = _tonnage_price_service.get_years(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/tonnages", response_model=ApiResponse[list[int]])
def get_tonnages(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
) -> ApiResponse[list[int]]:
    """获取所有吨位列表"""
    data = _tonnage_price_service.get_tonnages(db)
    return ApiResponse.ok(data=data)


@router.get("/export")
def export_excel(
    location: str | None = Query(None, description="采购基地"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出冲次单价 Excel。"""
    content, filename = _export_service.export(
        db,
        location=location.strip() if location else None,
        year=year,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/template")
def download_import_template(
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载冲次单价导入模板（名称 / 单位 / 单价）。"""
    content, filename = _import_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/upload",
    response_model=ApiResponse[StampingTonnagePriceImportResultVO],
)
async def upload_tonnage_price_excel(
    location: str = Form(..., description="采购基地（必填）"),
    year: int = Form(..., description="年度（必填）"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_UPLOAD_UPLOAD)),
) -> ApiResponse[StampingTonnagePriceImportResultVO]:
    """同步导入冲次单价 Excel；基地与年度必选；仅支持 .xlsx。"""
    content = await file.read()
    result = _import_service.import_excel(
        db,
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        year=year,
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.post(
    "/batch-delete",
    response_model=ApiResponse[StampingTonnagePriceBatchDeleteResultVO],
)
def batch_delete(
    body: StampingTonnagePriceBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_DELETE)),
) -> ApiResponse[StampingTonnagePriceBatchDeleteResultVO]:
    """按基地 + 年度批量删除冲次单价（仅删未审核；已通过跳过）。"""
    deleted_count, skipped = _tonnage_price_service.batch_delete_by_location_year(
        db,
        location=body.location,
        year=body.year,
    )

    message = f"已删除基地「{body.location}」{body.year} 年共 {deleted_count} 条"
    if skipped:
        message += f"，跳过已审核 {skipped} 条"
    return ApiResponse.ok(
        data=StampingTonnagePriceBatchDeleteResultVO(
            location=body.location.strip(),
            year=body.year,
            deleted_count=deleted_count,
            skipped_approved_count=skipped,
            message=message,
        ),
        message=message,
    )


@router.post(
    "/batch-approve",
    response_model=ApiResponse[StampingTonnagePriceBatchAuditResultVO],
)
def batch_approve(
    body: StampingTonnagePriceBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_APPROVE)),
) -> ApiResponse[StampingTonnagePriceBatchAuditResultVO]:
    """按基地 + 年度批量审核通过。"""
    result = _tonnage_price_service.batch_approve(db, body, current_user=current_user)
    message = f"已审核通过 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过已审核 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[StampingTonnagePriceBatchAuditResultVO],
)
def batch_reverse_audit(
    body: StampingTonnagePriceBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_REVERSE)),
) -> ApiResponse[StampingTonnagePriceBatchAuditResultVO]:
    """按基地 + 年度批量反审核。"""
    result = _tonnage_price_service.batch_reverse_audit(db, body, current_user=current_user)
    message = f"已反审核 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过非已审 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post("/bulk", response_model=ApiResponse[StampingTonnagePriceBulkUpsertResponse])
def bulk_upsert(
    items: list[StampingTonnagePriceCreate],
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_CREATE)),
) -> ApiResponse[StampingTonnagePriceBulkUpsertResponse]:
    """批量写入冲次单价（存在则更新，与 Excel 导入一致）"""
    created, updated, failed, skipped_approved = _tonnage_price_service.bulk_upsert(
        db, items, current_user=current_user
    )
    return ApiResponse.ok(
        data=StampingTonnagePriceBulkUpsertResponse(
            created=created,
            updated=updated,
            failed=failed,
            created_count=len(created),
            updated_count=len(updated),
            failed_count=len(failed),
            skipped_approved_count=skipped_approved,
        ),
        message=(
            f"批量写入完成: 新增 {len(created)}, 更新 {len(updated)}, "
            f"失败 {len(failed)}, 跳过已审核 {skipped_approved}"
        ),
    )


@router.post("", response_model=ApiResponse[StampingTonnagePriceResponse])
def create(
    body: StampingTonnagePriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_CREATE)),
) -> ApiResponse[StampingTonnagePriceResponse]:
    """创建冲次单价记录"""
    record = _tonnage_price_service.create(db, body, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.get("/{id}", response_model=ApiResponse[StampingTonnagePriceResponse])
def get_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
) -> ApiResponse[StampingTonnagePriceResponse]:
    """获取单个冲次单价记录"""
    record = _tonnage_price_service.get_by_id(db, id)
    return ApiResponse.ok(data=record, message="获取成功")


@router.put("/{id}", response_model=ApiResponse[StampingTonnagePriceResponse])
def update(
    id: int,
    body: StampingTonnagePriceUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_UPDATE)),
) -> ApiResponse[StampingTonnagePriceResponse]:
    """更新冲次单价记录"""
    record = _tonnage_price_service.update(db, id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{id}", response_model=ApiResponse[None])
def delete(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_DELETE)),
) -> ApiResponse[None]:
    """删除冲次单价记录"""
    _tonnage_price_service.delete(db, id)
    return ApiResponse.deleted(message="删除成功")
