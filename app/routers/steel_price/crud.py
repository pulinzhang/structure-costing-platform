"""钢材价格管理 API。"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.dto.steel_price_dto import (
    SteelPriceCreate,
    SteelPriceQuery,
    SteelPriceUpdate,
)
from app.services.steel_price import SteelPriceService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_price")
router = APIRouter(prefix="/api/steel-prices", tags=["钢材价格管理"])
_steel_price_service = SteelPriceService()


@router.get("")
def list_steel_prices(
    query: SteelPriceQuery = Depends(),
    db: Session = Depends(get_db),
):
    """分页浏览钢材价格。"""

    records, total, filters = _steel_price_service.paginate(db, query)
    return ApiResponse.list_(
        data=records,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条钢材价格",
        filters=filters,
    )


@router.get("/{record_id}")
def get_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
):
    """查看单条钢材价格详情。"""

    record = _steel_price_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="钢材价格记录不存在")
    return ApiResponse.success(data=record)


@router.post("")
def create_steel_price(
    body: SteelPriceCreate,
    db: Session = Depends(get_db),
):
    """手动新建一条钢材价格。"""

    record, error = _steel_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.success(data=record, message="新增成功")


@router.put("/{record_id}")
def update_steel_price(
    record_id: int,
    body: SteelPriceUpdate,
    db: Session = Depends(get_db),
):
    """更新钢材价格。"""

    record, error = _steel_price_service.update(db, record_id, body)
    if error:
        if "记录不存在" in error:
            raise HTTPException(status_code=404, detail=error)
        logger.error("更新钢材价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.success(data=record, message="更新成功")


@router.delete("/{record_id}")
def delete_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
):
    """删除钢材价格。"""

    success, error = _steel_price_service.delete(db, record_id)
    if not success:
        if "记录不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error or "记录不存在")
        logger.error("删除钢材价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="删除成功")


@router.post("/upload")
async def upload_steel_prices(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传标准十二列 Excel，按 ``(年度, 月份, 牌号, 厚度)`` 唯一键执行插入或修改。"""

    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {max_size_mb}MB")

    try:
        result = _steel_price_service.import_excel(
            db,
            file_content=file_content,
            filename=file.filename,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("处理钢材价格文件失败: filename=%s", file.filename)
        raise HTTPException(status_code=500, detail="钢材价格导入失败") from error

    message = (
        f"导入成功，新增 {result['created_count']} 条，"
        f"更新 {result['updated_count']} 条，共 {result['imported_count']} 条钢材价格"
    )
    return ApiResponse.success(data=result, message=message)
