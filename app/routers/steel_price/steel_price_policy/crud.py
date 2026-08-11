"""
钢价政策管理 API
采用严格主子表架构：政策主表 + 阶梯明细表
所有尺寸和金额字段全程使用 Decimal/Integer，绝不转为 float
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.database import DatabaseConfig, get_db
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemCreate,
    LadderItemUpdate,
    PolicyCreate,
    PolicyMatchRequest,
    PolicyQuery,
    PolicyUpdate,
)
from app.schemas.vo.steel_price_policy_vo import (
    ExportRow,
    ImportResultResponse,
    LadderItemResponse,
    PolicyDetailResponse,
    PolicyListResponse,
    PolicyMatchResponse,
    PolicyOptionsResponse,
    UploadTaskAcceptedResponse,
    UploadTaskProgressResponse,
)
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_POLICY_UPLOAD,
    AsyncTaskService,
)
from app.services.steel_price_policy import SteelPricePolicyService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_price_policy")
router = APIRouter(prefix="/api/steel-price-policies", tags=["钢价政策管理"])

# 默认分页大小常量
DEFAULT_PAGE_SIZE = 100

_policy_service = SteelPricePolicyService()
_async_task_service = AsyncTaskService()


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


def _process_policy_upload_in_background(
    task_id: str,
    file_content: bytes,
    filename: str,
    year: int,
    month: int,
) -> None:
    """
    后台线程执行政策 Excel 解析与入库。
    必须在独立线程中运行，禁止写成 async（否则会阻塞 Event Loop）。
    进度写入独立异步任务库；主数据使用业务 Session 大事务。
    """
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    def on_progress(progress: int, msg: str) -> None:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=progress,
            message=msg,
        )

    try:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=1,
            message="后台开始解析...",
        )
        result = _policy_service.import_from_parser(
            db,
            file_content=file_content,
            filename=filename,
            year=year,
            month=month,
            progress_callback=on_progress,
        )
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_COMPLETED,
            progress=100,
            message=(
                f"导入完成：新增 {result.created_count} 条，"
                f"更新 {result.updated_count} 条，共 {result.total} 条"
            ),
            result=result.model_dump(),
        )
    except ValueError as error:
        logger.warning("政策导入业务失败: task_id=%s error=%s", task_id, error)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=str(error),
        )
    except Exception as error:
        logger.exception("政策导入异常: task_id=%s filename=%s", task_id, filename)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=f"解析异常: {error}",
        )
    finally:
        db.close()


# =============================================================================
# 政策主表查询
# =============================================================================

@router.get(
    "",
    response_model=ApiResponse[PageResult[PolicyListResponse]],
)
def list_policies(
    query: PolicyQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[PolicyListResponse]]:
    """分页筛选政策列表"""
    records, total, options = _policy_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条政策",
        filters=options.model_dump() if options else None,
    )


@router.get(
    "/options",
    response_model=ApiResponse[PolicyOptionsResponse],
)
def get_policy_options(
    db: Session = Depends(get_db),
) -> ApiResponse[PolicyOptionsResponse]:
    """获取政策筛选下拉选项"""
    _, _, options = _policy_service.paginate(db, PolicyQuery(page=1, size=1))
    return ApiResponse.ok(data=options)


# =============================================================================
# Excel 导入（异步：立即返回 task_id，前端轮询进度）
# =============================================================================

@router.post(
    "/upload",
    response_model=ApiResponse[UploadTaskAcceptedResponse],
)
async def upload_policy_excel(
    year: int = Form(..., ge=2000, le=2100, description="生效年度"),
    month: int = Form(..., ge=1, le=12, description="生效月份（1-12）"),
    file: UploadFile = File(..., description="一事一议价格 Excel 文件"),
) -> ApiResponse[UploadTaskAcceptedResponse]:
    """
    上传钢价政策 Excel，立即返回 task_id，后台线程解析入库。
    任务进度写入独立异步任务库，不复用业务 Session。
    主数据仍在单一大事务中导入（全部成功或全部回滚）。
    """
    file_content = await file.read()

    try:
        _policy_service.validate_upload(file_content, file.filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_POLICY_UPLOAD,
        message="已提交解析队列",
    )
    AsyncTaskService.submit(
        _process_policy_upload_in_background,
        task.task_id,
        file_content,
        file.filename or "policy.xlsx",
        year,
        month,
    )

    return ApiResponse.ok(
        data=UploadTaskAcceptedResponse(task_id=task.task_id),
        message="上传成功，后台开始解析",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[UploadTaskProgressResponse],
)
def get_upload_task_progress(
    task_id: str,
) -> ApiResponse[UploadTaskProgressResponse]:
    """查询政策上传/解析任务进度（独立异步任务库）"""
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_POLICY_UPLOAD:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = ImportResultResponse.model_validate(result_raw) if result_raw else None
    updated_at_value = task.get("updated_at")
    updated_at = (
        updated_at_value.timestamp()
        if hasattr(updated_at_value, "timestamp")
        else float(updated_at_value or 0)
    )

    return ApiResponse.ok(
        data=UploadTaskProgressResponse(
            status=task.get("status") or STATUS_PENDING,
            progress=int(task.get("progress") or 0),
            msg=task.get("message") or "",
            result=result,
            updated_at=updated_at,
        ),
    )


# =============================================================================
# Excel 导出
# =============================================================================

@router.get("/export")
def export_policies_excel(
    year: Optional[int] = None,
    month: Optional[int] = None,
    steel_mill: Optional[str] = None,
    category_name: Optional[str] = None,
    grade_value: Optional[str] = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    导出钢价政策主子表联合数据为 Excel，用于测试部门核对。
    """
    excel_bytes, filename = _policy_service.generate_export_excel_bytes(
        db,
        year=year,
        month=month,
        steel_mill=steel_mill,
        category_name=category_name.strip() if category_name else None,
        grade_value=grade_value.strip() if grade_value else None,
    )

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.get(
    "/export-preview",
    response_model=ApiResponse[PageResult[ExportRow]],
)
def export_policies_preview(
    year: Optional[int] = None,
    month: Optional[int] = None,
    steel_mill: Optional[str] = None,
    category_name: Optional[str] = None,
    grade_value: Optional[str] = None,
    page: int = 1,
    size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[ExportRow]]:
    """
    预览导出数据（主子表联合查询，分页）
    """
    category = category_name.strip() if category_name else None
    grade = grade_value.strip() if grade_value else None
    mill = steel_mill.strip() if steel_mill else None
    records = _policy_service.get_export_data(
        db,
        year=year,
        month=month,
        steel_mill=mill,
        category_name=category,
        grade_value=grade,
        skip=(page - 1) * size,
        limit=size,
    )
    total = _policy_service.count_export_data(
        db,
        year=year,
        month=month,
        steel_mill=mill,
        category_name=category,
        grade_value=grade,
    )
    return ApiResponse.list_(items=records, total=total, page=page, page_size=size)


# =============================================================================
# 条件批量删除
# =============================================================================

@router.delete(
    "/batch",
    response_model=ApiResponse[None],
)
def batch_delete_policies(
    year: Optional[int] = None,
    month: Optional[int] = None,
    steel_mill: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
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

@router.get(
    "/{policy_id}",
    response_model=ApiResponse[PolicyDetailResponse],
)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[PolicyDetailResponse]:
    """获取政策详情（含完整阶梯明细，按 sort_order + id 排序）"""
    record = _policy_service.get_by_id(db, policy_id)
    if record is None:
        raise HTTPException(status_code=404, detail="政策记录不存在")
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[PolicyDetailResponse],
)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[PolicyDetailResponse]:
    """原子创建政策（含阶梯明细）"""
    record = _map_service_error(_policy_service.create(db, body), "政策")
    return ApiResponse.created(data=record, message="政策创建成功")


@router.put(
    "/{policy_id}",
    response_model=ApiResponse[PolicyDetailResponse],
)
def update_policy(
    policy_id: int,
    body: PolicyUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[PolicyDetailResponse]:
    """更新政策（支持更新政策头字段和整组替换阶梯明细）"""
    record = _map_service_error(_policy_service.update(db, policy_id, body), "政策")
    return ApiResponse.updated(data=record, message="政策更新成功")


@router.delete(
    "/{policy_id}",
    response_model=ApiResponse[None],
)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除政策（含级联删除全部阶梯明细）"""
    success, error = _policy_service.delete(db, policy_id)
    if not success:
        _map_service_error((None, error), "政策")
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="政策删除成功")


# =============================================================================
# 阶梯明细独立 CRUD
# =============================================================================

@router.post(
    "/{policy_id}/items",
    response_model=ApiResponse[LadderItemResponse],
)
def add_ladder_item(
    policy_id: int,
    body: LadderItemCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[LadderItemResponse]:
    """向指定政策新增一条阶梯明细"""
    record = _map_service_error(_policy_service.add_item(db, policy_id, body), "阶梯明细")
    return ApiResponse.created(data=record, message="阶梯明细新增成功")


@router.put(
    "/{policy_id}/items/{item_id}",
    response_model=ApiResponse[LadderItemResponse],
)
def update_ladder_item(
    policy_id: int,
    item_id: int,
    body: LadderItemUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[LadderItemResponse]:
    """更新指定政策下的单条阶梯明细"""
    record = _map_service_error(_policy_service.update_item(db, item_id, body), "阶梯明细")
    return ApiResponse.updated(data=record, message="阶梯明细更新成功")


@router.delete(
    "/{policy_id}/items/{item_id}",
    response_model=ApiResponse[None],
)
def delete_ladder_item(
    policy_id: int,
    item_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除指定政策下的单条阶梯明细"""
    success, error = _policy_service.delete_item(db, item_id)
    if not success:
        _map_service_error((None, error), "阶梯明细")
        raise HTTPException(status_code=400, detail=error or "删除失败")
    return ApiResponse.deleted(message="阶梯明细删除成功")


# =============================================================================
# 阶梯匹配
# =============================================================================

@router.post(
    "/match",
    response_model=ApiResponse[PolicyMatchResponse],
)
def match_ladder(
    body: PolicyMatchRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[PolicyMatchResponse]:
    """
    根据政策维度与尺寸值，匹配阶梯明细并返回加减价金额。
    - 命中多条时以 sort_order 升序、id 升序确定优先级
    - price_adjustment 为整数（元/吨）
    """
    result = _policy_service.match(db, body)
    return ApiResponse.ok(data=result)
