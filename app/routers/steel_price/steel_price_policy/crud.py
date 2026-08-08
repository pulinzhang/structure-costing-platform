"""
钢价政策管理 API
采用严格主子表架构：政策主表 + 阶梯明细表
所有尺寸和金额字段全程使用 Decimal/Integer，绝不转为 float
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemCreate,
    LadderItemUpdate,
    PolicyCreate,
    PolicyMatchRequest,
    PolicyQuery,
    PolicyUpdate,
)
from app.services.steel_price_policy import SteelPricePolicyService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_price_policy")
router = APIRouter(prefix="/api/steel-price-policies", tags=["钢价政策管理"])

_policy_service = SteelPricePolicyService()


def _map_service_error(
    result: tuple,
    entity_name: str = "记录",
) -> Optional[object]:
    """
    解析 Service 层返回的 (record, error) 元组。
    - error 为 None → 返回 record
    - error 含"不存在" → raise 404
    - 其它 error → raise 400
    """
    record, error = result
    if error is None:
        return record
    if "不存在" in (error or ""):
        raise HTTPException(status_code=404, detail=error)
    raise HTTPException(status_code=400, detail=error)


# =============================================================================
# 政策主表查询
# =============================================================================

@router.get("")
def list_policies(
    query: PolicyQuery = Depends(),
    db: Session = Depends(get_db),
):
    """
    分页筛选政策列表
    """
    records, total, options = _policy_service.paginate(db, query)
    return ApiResponse.list_(
        data=[r.model_dump() for r in records],
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条政策",
        filters=options.model_dump() if options else None,
    )


@router.get("/options")
def get_policy_options(
    db: Session = Depends(get_db),
):
    """
    获取政策筛选下拉选项
    """
    _, _, options = _policy_service.paginate(
        db, PolicyQuery(page=1, size=1)
    )
    return ApiResponse.success(data=options.model_dump())


# =============================================================================
# Excel 导入
# =============================================================================

@router.post("/upload")
async def upload_policy_excel(
    year: int = Form(..., ge=2000, le=2100, description="生效年度"),
    month: int = Form(..., ge=1, le=12, description="生效月份（1-12）"),
    file: UploadFile = File(..., description="一事一议价格 Excel 文件"),
    db: Session = Depends(get_db),
):
    """
    上传钢价政策 Excel，按年度+月份执行 upsert。
    同一 (year, month, steel_mill, category, policy_type, grade, base_thickness) 的政策会被替换。
    """
    file_content = await file.read()

    try:
        _policy_service.validate_upload(file_content, file.filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        result = _policy_service.import_from_parser(
            db,
            file_content=file_content,
            filename=file.filename,
            year=year,
            month=month,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("处理钢价政策文件失败: filename=%s", file.filename)
        raise HTTPException(status_code=500, detail="钢价政策导入失败") from error

    return ApiResponse.success(
        data=result.model_dump(),
        message=f"导入完成，新增 {result.created_count} 条，更新 {result.updated_count} 条，跳过 {result.skipped_count} 条",
    )


# =============================================================================
# Excel 导出
# =============================================================================

@router.get("/export")
def export_policies_excel(
    year: Optional[int] = None,
    month: Optional[int] = None,
    steel_mill: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    导出钢价政策主子表联合数据为 Excel，用于测试部门核对。
    """
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

    excel_bytes, filename = _policy_service.generate_export_excel_bytes(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill,
    )

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.get("/export-preview")
def export_policies_preview(
    year: Optional[int] = None,
    month: Optional[int] = None,
    steel_mill: Optional[str] = None,
    page: int = 1,
    size: int = 100,
    db: Session = Depends(get_db),
):
    """
    预览导出数据（主子表联合查询，分页）
    """
    records = _policy_service.get_export_data(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill.strip() if steel_mill else None,
        skip=(page - 1) * size,
        limit=size,
    )
    total = _policy_service.count_export_data(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill.strip() if steel_mill else None,
    )
    return ApiResponse.list_(data=[r.model_dump() for r in records], total=total, page=page, page_size=size)


# =============================================================================
# 条件批量删除
# =============================================================================

@router.delete("/batch")
def batch_delete_policies(
    year: Optional[int] = None,
    month: Optional[int] = None,
    steel_mill: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    根据条件批量删除政策（年度、月份、钢厂）。
    至少需要一个条件，否则返回 400。
    """
    count, error = _policy_service.delete_by_conditions(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill,
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.deleted(message=f"成功删除 {count} 条政策")


# =============================================================================
# 政策主表 CRUD
# =============================================================================

@router.get("/{policy_id}")
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    """
    获取政策详情（含完整阶梯明细，按 sort_order + id 排序）
    """
    record = _policy_service.get_by_id(db, policy_id)
    if record is None:
        raise HTTPException(status_code=404, detail="政策记录不存在")
    return ApiResponse.success(data=record)


@router.post("")
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
):
    """
    原子创建政策（含阶梯明细）
    """
    record = _map_service_error(_policy_service.create(db, body), "政策")
    return ApiResponse.created(data=record, message="政策创建成功")


@router.put("/{policy_id}")
def update_policy(
    policy_id: int,
    body: PolicyUpdate,
    db: Session = Depends(get_db),
):
    """
    更新政策（支持更新政策头字段和整组替换阶梯明细）
    """
    record = _map_service_error(_policy_service.update(db, policy_id, body), "政策")
    return ApiResponse.updated(data=record, message="政策更新成功")


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
):
    """
    删除政策（含级联删除全部阶梯明细）
    """
    success, error = _policy_service.delete(db, policy_id)
    if not success:
        _map_service_error((None, error), "政策")
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="政策删除成功")


# =============================================================================
# 阶梯明细独立 CRUD
# =============================================================================

@router.post("/{policy_id}/items")
def add_ladder_item(
    policy_id: int,
    body: LadderItemCreate,
    db: Session = Depends(get_db),
):
    """
    向指定政策新增一条阶梯明细
    """
    record = _map_service_error(_policy_service.add_item(db, policy_id, body), "阶梯明细")
    return ApiResponse.created(data=record, message="阶梯明细新增成功")


@router.put("/{policy_id}/items/{item_id}")
def update_ladder_item(
    policy_id: int,
    item_id: int,
    body: LadderItemUpdate,
    db: Session = Depends(get_db),
):
    """
    更新指定政策下的单条阶梯明细
    """
    record = _map_service_error(_policy_service.update_item(db, item_id, body), "阶梯明细")
    return ApiResponse.updated(data=record, message="阶梯明细更新成功")


@router.delete("/{policy_id}/items/{item_id}")
def delete_ladder_item(
    policy_id: int,
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    删除指定政策下的单条阶梯明细
    """
    success, error = _policy_service.delete_item(db, item_id)
    if not success:
        _map_service_error((None, error), "阶梯明细")
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="阶梯明细删除成功")


# =============================================================================
# 阶梯匹配
# =============================================================================

@router.post("/match")
def match_ladder(
    body: PolicyMatchRequest,
    db: Session = Depends(get_db),
):
    """
    根据政策维度与尺寸值，匹配阶梯明细并返回加减价金额。
    - 命中多条时以 sort_order 升序、id 升序确定优先级
    - price_adjustment 为整数（元/吨）
    - 所有尺寸字段以 Decimal 精确传递
    """
    result = _policy_service.match(db, body)
    return ApiResponse.success(data=result.model_dump())
