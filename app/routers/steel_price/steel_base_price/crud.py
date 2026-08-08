"""
钢材基准价格管理 API
基准价格表：记录每个基地、每个钢厂、每个牌号在每个月的基准价格
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dto.steel_base_price_dto import (
    FilterOptions,
    ExportRow as SteelBasePriceExportRow,
)
from app.schemas.vo.steel_base_price_vo import SteelBasePriceResponse
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.services.steel_base_price import SteelBasePriceService
from app.services.steel_base_price import SteelBasePriceExportService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_base_price")
router = APIRouter(prefix="/api/steel-base-prices", tags=["钢材基准价格管理"])

_steel_base_price_service = SteelBasePriceService()
_steel_base_price_export_service = SteelBasePriceExportService()


@router.get("")
def list_base_prices(
    query: SteelBasePriceQuery = Depends(),
    db: Session = Depends(get_db),
):
    """分页浏览基准价格。"""
    records, total, filters = _steel_base_price_service.paginate(db, query)
    return ApiResponse.list_(
        data=records,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条基准价格",
        filters=filters,
    )


@router.get("/options")
def get_base_price_options(
    db: Session = Depends(get_db),
):
    """获取基准价格筛选下拉选项。"""
    _, _, filters = _steel_base_price_service.paginate(db, SteelBasePriceQuery(page=1, size=1))
    return ApiResponse.success(data=filters.model_dump())


@router.get("/export-preview")
def export_base_prices_preview(
    year: Optional[int] = None,
    month: Optional[int] = None,
    location: Optional[str] = None,
    steel_mill: Optional[str] = None,
    spec: Optional[str] = None,
    db: Session = Depends(get_db),

):
    """预览导出数据。"""
    records = _steel_base_price_service.list_for_export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        spec=spec,
    )
    return ApiResponse.list_(data=records, total=len(records), page=1, page_size=len(records))


@router.get("/export")
def export_base_prices_excel(
    year: Optional[int] = None,
    month: Optional[int] = None,
    location: Optional[str] = None,
    steel_mill: Optional[str] = None,
    spec: Optional[str] = None,
    db: Session = Depends(get_db),

):
    """导出基准价格数据为 Excel。"""
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

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
):
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


@router.post("/upload")
async def upload_base_prices(
    year: int,
    month: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

    return ApiResponse.success(
        data=result,
        message=f"导入完成，新增 {result['created_count']} 条，更新 {result['updated_count']} 条，共 {result['total']} 条",
    )


# =============================================================================
# 资源型路由（/{record_id} 必须放在具体路径路由之后）
# =============================================================================

@router.get("/{record_id}")
def get_base_price(
    record_id: int,
    db: Session = Depends(get_db),
):
    """查看单条基准价格详情。"""
    record = _steel_base_price_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="基准价格记录不存在")
    return ApiResponse.success(data=record)


@router.post("")
def create_base_price(
    body: SteelBasePriceCreate,
    db: Session = Depends(get_db),
):
    """手动新建一条基准价格。"""
    record, error = _steel_base_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.success(data=record, message="新增成功")


@router.put("/{record_id}")
def update_base_price(
    record_id: int,
    body: SteelBasePriceUpdate,
    db: Session = Depends(get_db),
):
    """更新基准价格。"""
    record, error = _steel_base_price_service.update(db, record_id, body)
    if error:
        if "不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error)
        logger.error("更新基准价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.success(data=record, message="更新成功")


@router.delete("/{record_id}")
def delete_base_price(
    record_id: int,
    db: Session = Depends(get_db),
):
    """删除基准价格。"""
    success, error = _steel_base_price_service.delete(db, record_id)
    if not success:
        if "不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error or "记录不存在")
        logger.error("删除基准价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="删除成功")


# 文件结束
