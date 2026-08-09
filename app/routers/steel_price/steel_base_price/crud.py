"""
钢材基准价格 CRUD 路由
"""

from fastapi import APIRouter, Depends, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.response import ApiResponse
from app.services.steel_base_price import SteelBasePriceService
from app.services.steel_base_price.steel_base_price_export_service import SteelBasePriceExportService
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.steel_base_price_vo import (
    FilterOptionsVO,
    SteelBasePriceExportRow,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)


router = APIRouter(prefix="/api/steel-base-prices", tags=["钢材基准价格"])

_steel_base_price_service = SteelBasePriceService()
_steel_base_price_export_service = SteelBasePriceExportService()


def _build_filter_options_vo(service: SteelBasePriceService, db: Session) -> FilterOptionsVO:
    """从 Repository 获取 FilterOptions 并转换为 VO"""
    from app.schemas.dto.steel_base_price_dto import FilterOptions
    raw: FilterOptions = service.get_filter_options(db)
    return FilterOptionsVO(
        years=raw.years,
        months=raw.months,
        locations=raw.locations,
        steel_mills=raw.steel_mills,
        category_names=raw.category_names,
        grades=raw.grades,
        specs=raw.specs,
    )


@router.get(
    "",
    response_model=ApiResponse[list[SteelBasePriceResponse]],
)
def list_base_prices(
    query: SteelBasePriceQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[list[SteelBasePriceResponse]]:
    """
    分页查询基准价格列表。
    """
    items, total = _steel_base_price_service.paginate(db, query)

    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get(
    "/options",
    response_model=ApiResponse[FilterOptionsVO],
)
def get_base_price_options(
    db: Session = Depends(get_db),
) -> ApiResponse[FilterOptionsVO]:
    """获取筛选下拉选项（年度/月份/基地/钢厂等）。"""
    filters = _build_filter_options_vo(_steel_base_price_service, db)
    return ApiResponse.ok(data=filters)


@router.get(
    "/export-preview",
    response_model=ApiResponse[list[SteelBasePriceExportRow]],
)
def export_preview(
    year: int | None = Query(None, ge=2000, le=2100, description="订单发布年份"),
    month: int | None = Query(None, ge=1, le=12, description="订单发布月份"),
    location: str | None = Query(None, description="采购基地"),
    steel_mill: str | None = Query(None, description="中标钢厂"),
    spec: str | None = Query(None, description="规格"),
    page: int | None = Query(None, ge=1, description="页码（前端分页用）"),
    size: int | None = Query(None, ge=1, le=5000, description="每页条数"),
    db: Session = Depends(get_db),
) -> ApiResponse[list[SteelBasePriceExportRow]]:
    """导出预览：返回筛选后的基准价格数据（前端分页）。"""
    page_size = size or 5000
    records, total = _steel_base_price_service.list_for_export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        spec=spec,
        page=page,
        page_size=page_size,
    )
    if page is not None:
        return ApiResponse.list_(
            items=records,
            total=total,
            page=page,
            page_size=page_size,
            message="查询成功",
        )
    return ApiResponse.ok(data=records)


@router.get(
    "/export-download",
    response_model=None,
)
def export_download(
    year: int | None = Query(None, ge=2000, le=2100, description="订单发布年份"),
    month: int | None = Query(None, ge=1, le=12, description="订单发布月份"),
    location: str | None = Query(None, description="采购基地"),
    steel_mill: str | None = Query(None, description="中标钢厂"),
    spec: str | None = Query(None, description="规格"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """下载基准价格 Excel 文件。"""
    content, filename = _steel_base_price_export_service.export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        spec=spec,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename*=UTF-8\'\'{filename}'},
    )


@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelBasePriceResponse],
)
def get_base_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceResponse]:
    """获取单条基准价格记录。"""
    record = _steel_base_price_service.get_by_id(db, record_id)
    if record is None:
        return ApiResponse.fail(message="记录不存在", code=404)
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[SteelBasePriceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_base_price(
    body: SteelBasePriceCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceResponse]:
    """创建基准价格记录。"""
    record, error = _steel_base_price_service.create(db, body)
    if error:
        return ApiResponse.fail(message=error, code=400)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id}",
    response_model=ApiResponse[SteelBasePriceResponse],
)
def update_base_price(
    record_id: int,
    body: SteelBasePriceUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceResponse]:
    """更新基准价格记录。"""
    record, error = _steel_base_price_service.update(db, record_id, body)
    if error:
        return ApiResponse.fail(message=error, code=400)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[None],
)
def delete_base_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除基准价格记录。"""
    ok, error = _steel_base_price_service.delete(db, record_id)
    if not ok:
        return ApiResponse.fail(message=error or "删除失败", code=404)
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[dict],
)
def batch_delete_base_prices(
    year: int = Query(..., ge=2000, le=2100, description="订单发布年份"),
    month: int = Query(..., ge=1, le=12, description="订单发布月份"),
    location: str | None = Query(None, description="采购基地"),
    steel_mill: str | None = Query(None, description="中标钢厂"),
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """按条件批量删除基准价格记录（年度+月份必须同时指定）。"""
    ok, error = _steel_base_price_service.batch_delete(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
    )
    if not ok:
        return ApiResponse.fail(message=error or "批量删除失败", code=400)
    return ApiResponse.ok(data={"year": year, "month": month}, message="批量删除成功")


@router.post(
    "/import",
    response_model=ApiResponse[SteelBasePriceImportResultResponse],
)
async def import_base_price(
    file: UploadFile = File(...),
    year: int = Query(..., ge=2000, le=2100, description="生效年度"),
    month: int = Query(..., ge=1, le=12, description="生效月份"),
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceImportResultResponse]:
    """导入 Excel 文件，upsert 基准价格数据。"""
    content = await file.read()
    result = _steel_base_price_service.import_excel(
        db,
        file_content=content,
        filename=file.filename or "unknown.xlsx",
        year=year,
        month=month,
    )
    return ApiResponse.ok(data=result, message="导入完成")