"""
焊接单价路由
API 接口定义
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.bom_welding_unit_price_dto import (
    BomWeldingUnitPriceBatchApproveDTO,
    BomWeldingUnitPriceBatchDeleteDTO,
    BomWeldingUnitPriceBatchReverseAuditDTO,
    BomWeldingUnitPriceCreate,
    BomWeldingUnitPriceQuery,
    BomWeldingUnitPriceUpdate,
)
from app.schemas.vo.bom_welding_unit_price_vo import (
    BomWeldingUnitPriceBatchAuditResultVO,
    BomWeldingUnitPriceBatchDeleteResultVO,
    BomWeldingUnitPriceBulkUpsertResponse,
    BomWeldingUnitPriceImportResultVO,
    BomWeldingUnitPriceResponse,
    WeldingStandardProcessCatalogItemVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_unit_price import BomWeldingUnitPriceService
from app.services.bom.welding_unit_price.export_service import (
    BomWeldingUnitPriceExportService,
)
from app.services.bom.welding_unit_price.import_service import (
    BomWeldingUnitPriceImportService,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom/welding-unit-price", tags=["焊接单价 API"])

_welding_unit_price_service = BomWeldingUnitPriceService()
_export_service = BomWeldingUnitPriceExportService()
_import_service = BomWeldingUnitPriceImportService()


@router.get("/list", response_model=ApiResponse[list[BomWeldingUnitPriceResponse]])
def list_all(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_VIEW)),
) -> ApiResponse[list[BomWeldingUnitPriceResponse]]:
    """获取所有焊接单价列表"""
    data = _welding_unit_price_service.list_all(db)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get(
    "/by-year/{year}",
    response_model=ApiResponse[list[BomWeldingUnitPriceResponse]],
)
def list_by_year(
    year: int,
    location: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_VIEW)),
) -> ApiResponse[list[BomWeldingUnitPriceResponse]]:
    """获取指定年份的焊接单价；传入 location 时按基地过滤"""
    if location:
        data = _welding_unit_price_service.list_by_location_year(db, location, year)
    else:
        data = _welding_unit_price_service.list_by_year(db, year)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get(
    "/paginate",
    response_model=ApiResponse[PageResult[BomWeldingUnitPriceResponse]],
)
def paginate(
    query: BomWeldingUnitPriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_VIEW)),
) -> ApiResponse[PageResult[BomWeldingUnitPriceResponse]]:
    """分页查询焊接单价"""
    rows, total, filters = _welding_unit_price_service.paginate(db, query)
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
        require_any_perm(
            Perm.BOM_WELDING_UNIT_PRICE_VIEW,
            Perm.BOM_WELDING_UNIT_PRICE_UPLOAD_VIEW,
        )
    ),
) -> ApiResponse[list[str]]:
    """获取所有基地列表"""
    data = _welding_unit_price_service.get_locations(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/years", response_model=ApiResponse[list[int]])
def get_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_VIEW)),
) -> ApiResponse[list[int]]:
    """获取所有年份列表"""
    data = _welding_unit_price_service.get_years(db)
    return ApiResponse.ok(data=data)


@router.get("/export")
def export_excel(
    location: str | None = Query(None, description="采购基地"),
    year: int | None = Query(None, ge=2000, le=2100, description="年份"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_EXPORT)),
) -> StreamingResponse:
    """按当前筛选条件导出焊接单价 Excel。"""
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


@router.get(
    "/standard-catalog",
    response_model=ApiResponse[list[WeldingStandardProcessCatalogItemVO]],
)
def list_standard_catalog(
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_UPLOAD_VIEW)),
) -> ApiResponse[list[WeldingStandardProcessCatalogItemVO]]:
    """焊接标准工艺目录（导入名称/单位须与此完全一致）。"""
    data = _import_service.list_standard_catalog()
    return ApiResponse.ok(data=data, message=f"标准工艺 {len(data)} 项")


@router.get("/template")
def download_import_template(
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载焊接单价导入模板（含标准工艺目录工作表）。"""
    content, filename = _import_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/upload",
    response_model=ApiResponse[BomWeldingUnitPriceImportResultVO],
)
async def upload_welding_unit_price_excel(
    location: str = Form(..., description="采购基地（必填）"),
    year: int = Form(..., description="年度（必填）"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[BomWeldingUnitPriceImportResultVO]:
    """同步导入焊接单价 Excel；基地与年度必选；仅支持 .xlsx。"""
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
    response_model=ApiResponse[BomWeldingUnitPriceBatchDeleteResultVO],
)
def batch_delete(
    body: BomWeldingUnitPriceBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_DELETE)),
) -> ApiResponse[BomWeldingUnitPriceBatchDeleteResultVO]:
    """按基地 + 年度批量删除焊接单价（仅删未审核；已通过跳过）。"""
    deleted_count, skipped = _welding_unit_price_service.batch_delete_by_location_year(
        db,
        location=body.location,
        year=body.year,
    )

    message = f"已删除基地「{body.location}」{body.year} 年共 {deleted_count} 条"
    if skipped:
        message += f"，跳过已审核 {skipped} 条"
    return ApiResponse.ok(
        data=BomWeldingUnitPriceBatchDeleteResultVO(
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
    response_model=ApiResponse[BomWeldingUnitPriceBatchAuditResultVO],
)
def batch_approve(
    body: BomWeldingUnitPriceBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_APPROVE)),
) -> ApiResponse[BomWeldingUnitPriceBatchAuditResultVO]:
    """按基地 + 年度批量审核通过。"""
    result = _welding_unit_price_service.batch_approve(db, body, current_user=current_user)
    message = f"已审核通过 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过已审核 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[BomWeldingUnitPriceBatchAuditResultVO],
)
def batch_reverse_audit(
    body: BomWeldingUnitPriceBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_REVERSE)),
) -> ApiResponse[BomWeldingUnitPriceBatchAuditResultVO]:
    """按基地 + 年度批量反审核。"""
    result = _welding_unit_price_service.batch_reverse_audit(db, body, current_user=current_user)
    message = f"已反审核 {result.updated_count} 条"
    if result.skipped_count:
        message += f"，跳过非已审 {result.skipped_count} 条"
    return ApiResponse.ok(data=result, message=message)


@router.post(
    "/bulk",
    response_model=ApiResponse[BomWeldingUnitPriceBulkUpsertResponse],
)
def bulk_upsert(
    items: list[BomWeldingUnitPriceCreate],
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_CREATE)),
) -> ApiResponse[BomWeldingUnitPriceBulkUpsertResponse]:
    """批量写入焊接单价（存在则更新）"""
    created, updated, failed, skipped_approved = _welding_unit_price_service.bulk_upsert(
        db, items, current_user=current_user
    )
    return ApiResponse.ok(
        data=BomWeldingUnitPriceBulkUpsertResponse(
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


@router.post(
    "",
    response_model=ApiResponse[BomWeldingUnitPriceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: BomWeldingUnitPriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_CREATE)),
) -> ApiResponse[BomWeldingUnitPriceResponse]:
    """创建焊接单价记录"""
    record = _welding_unit_price_service.create(db, body, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.get("/{id}", response_model=ApiResponse[BomWeldingUnitPriceResponse])
def get_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_VIEW)),
) -> ApiResponse[BomWeldingUnitPriceResponse]:
    """获取单个焊接单价记录"""
    record = _welding_unit_price_service.get_by_id(db, id)
    return ApiResponse.ok(data=record, message="获取成功")


@router.put("/{id}", response_model=ApiResponse[BomWeldingUnitPriceResponse])
def update(
    id: int,
    body: BomWeldingUnitPriceUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_UPDATE)),
) -> ApiResponse[BomWeldingUnitPriceResponse]:
    """更新焊接单价记录"""
    record = _welding_unit_price_service.update(db, id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete("/{id}", response_model=ApiResponse[None])
def delete(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_WELDING_UNIT_PRICE_DELETE)),
) -> ApiResponse[None]:
    """删除焊接单价记录"""
    _welding_unit_price_service.delete(db, id)
    return ApiResponse.deleted(message="删除成功")
