"""
钢材价格管理 API
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_dto import (
    SteelPriceCreate,
    SteelPriceQuery,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceResponse,
    SteelPriceImportResultResponse,
)
from app.services.steel_price import SteelPriceService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_price")
router = APIRouter(prefix="/api/steel-prices", tags=["钢材价格管理"])

_steel_price_service = SteelPriceService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[SteelPriceResponse]],
)
def list_steel_prices(
    query: SteelPriceQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[SteelPriceResponse]]:
    """分页浏览钢材价格。"""
    records, total, _ = _steel_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelPriceResponse],
)
def get_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """查看单条钢材价格。"""
    record = _steel_price_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[SteelPriceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_steel_price(
    body: SteelPriceCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """新增钢材价格。"""
    record, error = _steel_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.created(data=record, message="新增成功")


@router.put(
    "/{record_id}",
    response_model=ApiResponse[SteelPriceResponse],
)
def update_steel_price(
    record_id: int,
    body: SteelPriceUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """更新钢材价格。"""
    record, error = _steel_price_service.update(db, record_id, body)
    if error:
        if "不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[None],
)
def delete_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除钢材价格。"""
    success, error = _steel_price_service.delete(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail=error or "记录不存在")
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/upload",
    response_model=ApiResponse[SteelPriceImportResultResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_steel_prices(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceImportResultResponse]:
    """上传钢材价格 Excel，按唯一键执行 upsert。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx, .xls 文件")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="上传文件为空")

    try:
        result = _steel_price_service.import_excel(db, file_content=file_content, filename=file.filename)
    except Exception as error:
        logger.exception("处理钢材价格文件失败: filename=%s", file.filename)
        raise HTTPException(status_code=500, detail="导入失败") from error

    return ApiResponse.ok(
        data=result,
        message=f"导入完成，新增 {result.created_count} 条，更新 {result.updated_count} 条",
    )