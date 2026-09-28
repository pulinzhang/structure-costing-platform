"""
钢材基准价格 CRUD 路由
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceExportPreviewQuery,
    SteelBasePriceExportQuery,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.steel_base_price_vo import (
    SteelBasePriceBatchDeleteResultVO,
    SteelBasePriceExportRow,
    SteelBasePriceFilterOptionsVO,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_PENDING,
    TASK_TYPE_BASE_PRICE_IMPORT,
    AsyncTaskService,
)
from app.services.yishiyiyi.base_price.export.service import SteelBasePriceExportService
from app.services.yishiyiyi.base_price.service import SteelBasePriceService
from app.utils.response import ApiResponse

# 默认分页大小常量
DEFAULT_EXPORT_PAGE_SIZE = 5000


router = APIRouter(prefix="/api/yishiyiyi/base-price", tags=["钢材基准价格"])

_steel_base_price_service = SteelBasePriceService()
_steel_base_price_export_service = SteelBasePriceExportService()
_async_task_service = AsyncTaskService()


@router.get(
    "",
    response_model=ApiResponse[list[SteelBasePriceResponse]],
    summary="分页查询基准价格列表",
)
def list_base_prices(
    query: SteelBasePriceQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW, Perm.BASE_PRICE_UPLOAD_VIEW)
    ),
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
    response_model=ApiResponse[SteelBasePriceFilterOptionsVO],
    summary="获取筛选下拉选项",
)
def get_base_price_options(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW, Perm.BASE_PRICE_UPLOAD_VIEW)
    ),
) -> ApiResponse[SteelBasePriceFilterOptionsVO]:
    """获取筛选下拉选项（年度/月份/基地/钢厂等）。"""
    return ApiResponse.ok(data=_steel_base_price_service.get_filter_options(db))


@router.get(
    "/export-preview",
    response_model=ApiResponse[PageResult[SteelBasePriceExportRow] | list[SteelBasePriceExportRow]],
    summary="导出预览",
)
def export_preview(
    query: SteelBasePriceExportPreviewQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW)),
) -> ApiResponse[PageResult[SteelBasePriceExportRow] | list[SteelBasePriceExportRow]]:
    """导出预览。筛选：年度、月份、基地、钢厂、分类、牌号。"""
    page_size = query.size or DEFAULT_EXPORT_PAGE_SIZE
    records, total = _steel_base_price_service.list_for_export(
        db,
        year=query.year,
        month=query.month,
        location=query.location,
        steel_mill=query.steel_mill,
        category_name=query.category_name,
        grade=query.grade,
        page=query.page,
        page_size=page_size,
    )
    if query.page is not None:
        return ApiResponse.list_(
            items=records,
            total=total,
            page=query.page,
            page_size=page_size,
            message="查询成功",
        )
    return ApiResponse.ok(data=records)


@router.get(
    "/export-download",
    response_model=None,
    summary="下载基准价格 Excel",
)
def export_download(
    query: SteelBasePriceExportQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_EXPORT)),
) -> StreamingResponse:
    """下载基准价格 Excel。筛选：年度、月份、基地、钢厂、分类、牌号。"""
    content, filename = _steel_base_price_export_service.export(
        db,
        year=query.year,
        month=query.month,
        location=query.location,
        steel_mill=query.steel_mill,
        category_name=query.category_name,
        grade=query.grade,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/template", summary="下载基准价格导入模板")
def download_base_price_import_template(
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载基准价格导入模板（含样例宽表与填写说明）。"""
    content, filename = _steel_base_price_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/import",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
    summary="导入基准价格",
)
async def import_base_price(
    file: UploadFile = File(...),
    year: int = Query(..., ge=2000, le=2100, description="生效年度"),
    month: int = Query(..., ge=1, le=12, description="生效月份"),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """导入 Excel，立即返回 task_id，后台线程解析入库。"""
    accepted = _steel_base_price_service.start_import(
        file_content=await file.read(),
        filename=file.filename or "",
        year=year,
        month=month,
        current_user=current_user,
    )
    return ApiResponse.ok(
        data=accepted,
        message="上传成功，后台开始解析",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
    summary="查询基准价格导入任务进度",
)
def get_base_price_import_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询基准价格导入任务进度。"""
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_BASE_PRICE_IMPORT)

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = SteelBasePriceImportResultResponse.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.get(
    "/{record_id:int}",
    response_model=ApiResponse[SteelBasePriceResponse],
    summary="获取单条基准价格记录",
)
def get_base_price(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.BASE_PRICE_DOWNLOAD_VIEW, Perm.BASE_PRICE_UPLOAD_VIEW)
    ),
) -> ApiResponse[SteelBasePriceResponse]:
    """获取单条基准价格记录。"""
    record = _steel_base_price_service.get_by_id(db, record_id)
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[SteelBasePriceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建基准价格记录",
)
def create_base_price(
    body: SteelBasePriceCreate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[SteelBasePriceResponse]:
    """创建基准价格记录。"""
    record = _steel_base_price_service.create(db, body, current_user=current_user)
    return ApiResponse.created(data=record, message="创建成功")


@router.put(
    "/{record_id:int}",
    response_model=ApiResponse[SteelBasePriceResponse],
    summary="更新基准价格记录",
)
def update_base_price(
    record_id: int,
    body: SteelBasePriceUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_UPLOAD_UPLOAD)),
) -> ApiResponse[SteelBasePriceResponse]:
    """更新基准价格记录。"""
    record = _steel_base_price_service.update(db, record_id, body, current_user=current_user)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id:int}",
    response_model=ApiResponse[None],
    summary="删除基准价格记录",
)
def delete_base_price(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_DELETE)),
) -> ApiResponse[None]:
    """删除基准价格记录。"""
    _steel_base_price_service.delete(db, record_id)
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/batch-delete",
    response_model=ApiResponse[SteelBasePriceBatchDeleteResultVO],
    summary="按条件批量删除基准价格记录",
)
def batch_delete_base_prices(
    body: SteelBasePriceQuery,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BASE_PRICE_DOWNLOAD_DELETE)),
) -> ApiResponse[SteelBasePriceBatchDeleteResultVO]:
    """按条件批量删除基准价格记录（年度+月份必须同时指定）。"""
    result = _steel_base_price_service.batch_delete(
        db,
        year=body.year,
        month=body.month,
        location=body.location,
        steel_mill=body.steel_mill,
    )
    return ApiResponse.ok(data=result, message=result.message)
