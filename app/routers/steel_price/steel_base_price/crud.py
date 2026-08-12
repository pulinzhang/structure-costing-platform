"""
钢材基准价格 CRUD 路由
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.common.permissions.codes import Perm
from app.deps.permissions import require_any_perm, require_perm
from app.common.audit import display_name
from app.config import settings
from app.database import DatabaseConfig, get_db
from app.schemas.vo.user_vo import UserVO
from app.utils.logging_config import get_logger
from app.utils.response import ApiResponse
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_BASE_PRICE_IMPORT,
    AsyncTaskService,
)
from app.services.steel_base_price import SteelBasePriceService
from app.services.steel_base_price.steel_base_price_export_service import SteelBasePriceExportService
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.steel_base_price_vo import (
    FilterOptionsVO,
    SteelBasePriceExportRow,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)
from app.schemas.common import PageResult

# 默认分页大小常量
DEFAULT_EXPORT_PAGE_SIZE = 5000

logger = get_logger("router.steel_base_price")


class BatchDeleteResponse(BaseModel):
    """批量删除响应 VO"""
    year: int
    month: int


router = APIRouter(prefix="/api/steel-base-prices", tags=["钢材基准价格"])

_steel_base_price_service = SteelBasePriceService()
_steel_base_price_export_service = SteelBasePriceExportService()
_async_task_service = AsyncTaskService()


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


def _process_base_price_import_in_background(
    task_id: str,
    file_content: bytes,
    filename: str,
    year: int,
    month: int,
    current_user: UserVO,
) -> None:
    """后台线程解析基准价 Excel；独立 Session，不复用请求 db。"""
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
        result = _steel_base_price_service.import_excel(
            db,
            file_content=file_content,
            filename=filename,
            year=year,
            month=month,
            progress_callback=on_progress,
            current_user=current_user,
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
        logger.warning("基准价导入业务失败: task_id=%s error=%s", task_id, error)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=str(error),
        )
    except Exception as error:
        logger.exception("基准价导入异常: task_id=%s filename=%s", task_id, filename)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=f"解析异常: {error}",
        )
    finally:
        db.close()


@router.get(
    "",
    response_model=ApiResponse[list[SteelBasePriceResponse]],
)
def list_base_prices(
    query: SteelBasePriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_any_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW, Perm.BASE_PRICE_UPLOAD_VIEW)),
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
    current_user: UserVO = Depends(require_any_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW, Perm.BASE_PRICE_UPLOAD_VIEW)),
) -> ApiResponse[FilterOptionsVO]:
    """获取筛选下拉选项（年度/月份/基地/钢厂等）。"""
    filters = _build_filter_options_vo(_steel_base_price_service, db)
    return ApiResponse.ok(data=filters)


@router.get(
    "/export-preview",
    response_model=ApiResponse[PageResult[SteelBasePriceExportRow]],
)
def export_preview(
    year: int | None = Query(None, ge=2000, le=2100, description="订单发布年份"),
    month: int | None = Query(None, ge=1, le=12, description="订单发布月份"),
    location: str | None = Query(None, description="采购基地"),
    steel_mill: str | None = Query(None, description="中标钢厂"),
    category_name: str | None = Query(None, description="钢种大类"),
    grade: str | None = Query(None, description="牌号（模糊）"),
    spec: str | None = Query(None, description="规格"),
    page: int | None = Query(None, ge=1, description="页码（前端分页用）"),
    size: int | None = Query(None, ge=1, le=5000, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW)),
) -> ApiResponse[PageResult[SteelBasePriceExportRow]]:
    """导出预览：返回筛选后的基准价格数据（前端分页）。"""
    page_size = size or DEFAULT_EXPORT_PAGE_SIZE
    records, total = _steel_base_price_service.list_for_export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        category_name=category_name,
        grade=grade,
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
    category_name: str | None = Query(None, description="钢种大类"),
    grade: str | None = Query(None, description="牌号（模糊）"),
    spec: str | None = Query(None, description="规格"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_EXPORT)),
) -> StreamingResponse:
    """下载基准价格 Excel 文件。"""
    content, filename = _steel_base_price_export_service.export(
        db,
        year=year,
        month=month,
        location=location,
        steel_mill=steel_mill,
        category_name=category_name,
        grade=grade,
        spec=spec,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/import",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
)
async def import_base_price(
    file: UploadFile = File(...),
    year: int = Query(..., ge=2000, le=2100, description="生效年度"),
    month: int = Query(..., ge=1, le=12, description="生效月份"),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """导入 Excel，立即返回 task_id，后台线程解析入库。"""
    filename = file.filename or ""
    if not filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = "." + filename.split(".")[-1].lower()
    if ext not in {".xlsx", ".xls"}:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，仅支持 .xlsx / .xls",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB",
        )

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_BASE_PRICE_IMPORT,
        message="已提交解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    AsyncTaskService.submit(
        _process_base_price_import_in_background,
        task.task_id,
        content,
        filename,
        year,
        month,
        current_user,
    )

    return ApiResponse.ok(
        data=AsyncTaskAcceptedVO(task_id=task.task_id),
        message="上传成功，后台开始解析",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_base_price_import_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询基准价格导入任务进度。"""
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_BASE_PRICE_IMPORT:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = (
        SteelBasePriceImportResultResponse.model_validate(result_raw)
        if result_raw
        else None
    )
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelBasePriceResponse],
)
def get_base_price(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_any_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW, Perm.BASE_PRICE_UPLOAD_VIEW)),
) -> ApiResponse[SteelBasePriceResponse]:
    """获取单条基准价格记录。"""
    record = _steel_base_price_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[SteelBasePriceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_base_price(
    body: SteelBasePriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[SteelBasePriceResponse]:
    """创建基准价格记录。"""
    record, error = _steel_base_price_service.create(db, body, current_user=current_user)
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
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[SteelBasePriceResponse]:
    """更新基准价格记录。"""
    record, error = _steel_base_price_service.update(
        db, record_id, body, current_user=current_user
    )
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
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_DELETE)),
) -> ApiResponse[None]:
    """删除基准价格记录。"""
    ok, error = _steel_base_price_service.delete(db, record_id)
    if not ok:
        raise HTTPException(status_code=404, detail=error or "记录不存在")
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[BatchDeleteResponse],
)
def batch_delete_base_prices(
    body: SteelBasePriceQuery,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_DELETE)),
) -> ApiResponse[BatchDeleteResponse]:
    """按条件批量删除基准价格记录（年度+月份必须同时指定）。"""
    if body.year is None or body.month is None:
        return ApiResponse.fail(message="year 和 month 不能为空", code=400)
    ok, error = _steel_base_price_service.batch_delete(
        db,
        year=body.year,
        month=body.month,
        location=body.location,
        steel_mill=body.steel_mill,
    )
    if not ok:
        return ApiResponse.fail(message=error or "批量删除失败", code=400)
    return ApiResponse.ok(data=BatchDeleteResponse(year=body.year, month=body.month), message="批量删除成功")
