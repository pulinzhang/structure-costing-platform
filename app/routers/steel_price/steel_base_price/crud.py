"""
钢材基准价格管理 API
基准价格表：记录每个基地、每个钢厂、每个牌号在每个月的基准价格
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.database import get_db
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_base_price_dto import FilterOptions
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.steel_base_price_vo import (
    SteelBasePriceResponse,
    SteelBasePriceImportResultResponse,
)
from app.services.steel_base_price import SteelBasePriceService
from app.services.steel_base_price import SteelBasePriceExportService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_base_price")
router = APIRouter(prefix="/api/steel-base-prices", tags=["钢材基准价格管理"])

_steel_base_price_service = SteelBasePriceService()
_steel_base_price_export_service = SteelBasePriceExportService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[SteelBasePriceResponse]],
)
def list_base_prices(
    query: SteelBasePriceQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[SteelBasePriceResponse]]:
    """分页浏览基准价格。"""
    records, total, filters = _steel_base_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条基准价格",
        filters=filters.model_dump() if filters else None,
    )


@router.get(
    "/options",
    response_model=ApiResponse[dict],
)
def get_base_price_options(
    db: Session = Depends(get_db),
) -> ApiResponse[dict]:
    """获取基准价格筛选下拉选项。"""
    _, _, filters = _steel_base_price_service.paginate(db, SteelBasePriceQuery(page=1, size=1))
    return ApiResponse.ok(data=filters.model_dump())


@router.get(
    "/export-preview",
    response_model=ApiResponse[list[SteelBasePriceResponse]],
)
def export_base_prices_preview(
    year: Optional[int] = None,
    month: Optional[int] = None,
    location: Optional[str] = None,
    steel_mill: Optional[str] = None,
    spec: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ApiResponse[list[SteelBasePriceResponse]]:
    """预览导出数据。"""
    records = _steel_base_price_service.list_for_export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        spec=spec,
    )
    return ApiResponse.ok(data=records)


@router.get("/export")
def export_base_prices_excel(
    year: Optional[int] = None,
    month: Optional[int] = None,
    location: Optional[str] = None,
    steel_mill: Optional[str] = None,
    spec: Optional[str] = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """导出基准价格数据为 Excel。"""
    excel_bytes, filename = _steel_base_price_export_service.export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        spec=spec,
    )

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.delete("/batch")
def batch_delete_base_prices(
    year: int,
    month: int,
    location: Optional[str] = None,
    steel_mill: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """根据条件批量删除基准价格（年度+月份必须同时指定）。"""
    if not year or not month:
        raise HTTPException(status_code=400, detail="年度和月份必须同时指定")

    success, error = _steel_base_price_service.batch_delete(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
    )
    if not success:
        logger.error("批量删除基准价格失败: %s", error)
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/upload",
    response_model=ApiResponse[SteelBasePriceImportResultResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_base_prices(
    year: int,
    month: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceImportResultResponse]:
    """上传基准价格 Excel，按唯一键执行 upsert。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx, .xls 文件")
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="月份必须在 1-12 之间")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        result = _steel_base_price_service.import_excel(
            db,
            file_content=file_content,
            filename=file.filename,
            year=year,
            month=month,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("处理基准价格文件失败: filename=%s", file.filename)
        raise HTTPException(status_code=500, detail="基准价格导入失败") from error

    return ApiResponse.ok(
        data=result,
        message=f"导入完成，新增 {result.created_count} 条，更新 {result.updated_count} 条，共 {result.total} 条",
    )


# =============================================================================
# 资源型路由（/{record_id} 必须放在具体路径路由之后）
# =============================================================================

@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelBasePriceResponse],
)
def get_base_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceResponse]:
    """查看单条基准价格详情。"""
    record = _steel_base_price_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="基准价格记录不存在")
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
    """手动新建一条基准价格。"""
    record, error = _steel_base_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.created(data=record, message="新增成功")


@router.put(
    "/{record_id}",
    response_model=ApiResponse[SteelBasePriceResponse],
)
def update_base_price(
    record_id: int,
    body: SteelBasePriceUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelBasePriceResponse]:
    """更新基准价格。"""
    record, error = _steel_base_price_service.update(db, record_id, body)
    if error:
        if "不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error)
        logger.error("更新基准价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[None],
)
def delete_base_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除基准价格。"""
    success, error = _steel_base_price_service.delete(db, record_id)
    if not success:
        if "不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error or "记录不存在")
        logger.error("删除基准价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="删除成功")
