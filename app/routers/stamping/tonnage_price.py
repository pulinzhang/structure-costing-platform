"""
冲次费率路由
API 接口定义
"""

from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.services.stamping.tonnage_price_service import StampingTonnagePriceService
from app.services.stamping.tonnage_price_export_service import (
    StampingTonnagePriceExportService,
)
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceCreate,
    StampingTonnagePriceUpdate,
    StampingTonnagePriceQuery,
)
from app.schemas.vo.stamping_tonnage_price_vo import (
    StampingTonnagePriceResponse,
    StampingTonnagePriceBulkCreateResponse,
    StampingTonnagePriceCopyYearResponse,
)
from app.schemas.common.page_result import PageResult
from app.schemas.vo.user_vo import UserVO
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/stamping/tonnage-price", tags=["冲次费率 API"])

_tonnage_price_service = StampingTonnagePriceService()
_export_service = StampingTonnagePriceExportService()


@router.get("/list", response_model=ApiResponse[List[StampingTonnagePriceResponse]])
def list_all(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
):
    """获取所有冲次费率列表（按年份、吨位排序）"""
    data = _tonnage_price_service.list_all(db)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get("/by-year/{year}", response_model=ApiResponse[List[StampingTonnagePriceResponse]])
def list_by_year(
    year: int,
    location: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
):
    """获取指定年份的冲次费率；传入 location 时按基地过滤"""
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
):
    """分页查询冲次费率"""
    rows, total, filters = _tonnage_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/filters/locations", response_model=ApiResponse[List[str]])
def get_locations(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
):
    """获取所有基地列表"""
    data = _tonnage_price_service.get_locations(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/years", response_model=ApiResponse[List[int]])
def get_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
):
    """获取所有年份列表"""
    data = _tonnage_price_service.get_years(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/tonnages", response_model=ApiResponse[List[int]])
def get_tonnages(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
):
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
    """按当前筛选条件导出冲次费率 Excel。"""
    content, filename = _export_service.export(
        db,
        location=location.strip() if location else None,
        year=year,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.post("/copy-year", response_model=ApiResponse[StampingTonnagePriceCopyYearResponse])
def copy_from_year(
    location: str,
    source_year: int,
    target_year: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_COPY)),
):
    """在同一基地下，从源年份复制价格到目标年份"""
    created, skipped, failed = _tonnage_price_service.copy_from_year(
        db, location, source_year, target_year, current_user=current_user
    )
    return ApiResponse.ok(
        data=StampingTonnagePriceCopyYearResponse(
            location=location,
            source_year=source_year,
            target_year=target_year,
            created_count=created,
            skipped_count=skipped,
            failed=failed,
        ),
        message=(
            f"基地「{location}」从 {source_year} 复制到 {target_year}: "
            f"成功 {created}, 跳过 {skipped}"
        ),
    )


@router.post("/bulk", response_model=ApiResponse[StampingTonnagePriceBulkCreateResponse])
def bulk_create(
    items: List[StampingTonnagePriceCreate],
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_CREATE)),
):
    """批量创建冲次费率记录"""
    created, skipped, failed = _tonnage_price_service.bulk_create(
        db, items, current_user=current_user
    )
    return ApiResponse.ok(
        data=StampingTonnagePriceBulkCreateResponse(
            created=created,
            skipped=skipped,
            failed=failed,
            created_count=len(created),
            skipped_count=len(skipped),
            failed_count=len(failed),
        ),
        message=f"批量创建完成: 成功 {len(created)}, 跳过 {len(skipped)}, 失败 {len(failed)}",
    )


@router.post("", response_model=ApiResponse[StampingTonnagePriceResponse])
def create(
    body: StampingTonnagePriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_CREATE)),
):
    """创建冲次费率记录"""
    record, error = _tonnage_price_service.create(db, body, current_user=current_user)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.created(data=record, message="创建成功")


@router.get("/{id}", response_model=ApiResponse[StampingTonnagePriceResponse])
def get_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_VIEW)),
):
    """获取单个冲次费率记录"""
    record = _tonnage_price_service.get_by_id(db, id)
    if not record:
        raise HTTPException(status_code=404, detail=f"冲次费率记录不存在: id={id}")
    return ApiResponse.ok(data=record, message="获取成功")


@router.put("/{id}", response_model=ApiResponse[StampingTonnagePriceResponse])
def update(
    id: int,
    body: StampingTonnagePriceUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_UPDATE)),
):
    """更新冲次费率记录"""
    record, error = _tonnage_price_service.update(db, id, body, current_user=current_user)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return ApiResponse.ok(data=record, message="更新成功")


@router.delete("/{id}", response_model=ApiResponse[None])
def delete(
    id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_TONNAGE_DELETE)),
):
    """删除冲次费率记录"""
    success, error = _tonnage_price_service.delete(db, id)
    if not success:
        raise HTTPException(status_code=404, detail=error or "记录不存在")
    return ApiResponse.deleted(message="删除成功")
