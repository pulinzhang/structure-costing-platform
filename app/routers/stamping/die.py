"""冲压模具布点：上传、列表、导出、按作用域删除。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.stamping_die_dto import (
    StampingDieAllocRatioUpdate,
    StampingDiePartQuery,
    StampingDieScopeDTO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.stamping_die_vo import (
    StampingDieBatchDeleteResultVO,
    StampingDiePartDetailVO,
    StampingDiePartListVO,
    StampingDieProcessVO,
    StampingDieScopeFilterVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.async_task_service import (
    STATUS_PENDING,
    TASK_TYPE_STAMPING_DIE_UPLOAD,
    AsyncTaskService,
)
from app.services.stamping.die.crud.service import StampingDieService
from app.services.stamping.die.export.service import StampingDieExportService
from app.services.stamping.die.upload.upload_service import StampingDieUploadService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/stamping/die", tags=["冲压模具 API"])

_async_task_service = AsyncTaskService()
_die_service = StampingDieService()
_export_service = StampingDieExportService()


@router.get("/template")
def download_die_import_template(
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UPLOAD_VIEW)),
) -> StreamingResponse:
    content, filename = StampingDieUploadService.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/upload", response_model=ApiResponse[AsyncTaskAcceptedVO])
async def upload_die_layout(
    location: str = Form(...),
    vehicle_model: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    content = await file.read()
    accepted = StampingDieUploadService.start_upload(
        db=db,
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        vehicle_model=vehicle_model.strip(),
        current_user=current_user,
    )
    return ApiResponse.ok(data=accepted, message="上传成功，后台开始解析")


@router.get("/tasks/{task_id}", response_model=ApiResponse[AsyncTaskProgressVO])
def get_die_upload_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_STAMPING_DIE_UPLOAD)
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=AsyncTaskService.parse_result_json(task.get("result_json")),
        ),
    )


@router.get("/filters", response_model=ApiResponse[StampingDieScopeFilterVO])
def list_die_scope_filters(
    location: str | None = Query(None),
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.STAMPING_DIE_UPLOAD_VIEW, Perm.STAMPING_DIE_LIST_VIEW)
    ),
) -> ApiResponse[StampingDieScopeFilterVO]:
    return ApiResponse.ok(
        data=_die_service.list_scope_filters(db, location, year=year, month=month)
    )


@router.get("/parts", response_model=ApiResponse[PageResult[StampingDiePartListVO]])
def list_die_parts(
    query: StampingDiePartQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_LIST_VIEW)),
) -> ApiResponse[PageResult[StampingDiePartListVO]]:
    rows, total = _die_service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get("/parts/{part_id:int}", response_model=ApiResponse[StampingDiePartDetailVO])
def get_die_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_LIST_VIEW)),
) -> ApiResponse[StampingDiePartDetailVO]:
    return ApiResponse.ok(data=_die_service.get_part(db, part_id))


@router.patch("/processes/{process_id:int}", response_model=ApiResponse[StampingDieProcessVO])
def patch_die_process_alloc_ratio(
    process_id: int,
    body: StampingDieAllocRatioUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_LIST_UPDATE)),
) -> ApiResponse[StampingDieProcessVO]:
    return ApiResponse.updated(
        data=_die_service.update_alloc_ratio(db, process_id, body, current_user=current_user),
        message="分摊比例已更新",
    )


@router.get("/export")
def export_die_parts(
    location: str = Query(""),
    vehicle_model: str = Query(""),
    year: int | None = Query(None, ge=2000, le=2100, description="导出命中年"),
    month: int | None = Query(None, ge=1, le=12, description="导出命中月"),
    part_number: str | None = Query(None),
    include_expired: bool = Query(False, description="含已失效"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_LIST_EXPORT)),
) -> StreamingResponse:
    content, filename = _export_service.export_workbook(
        db,
        location=location,
        vehicle_model=vehicle_model,
        part_number=part_number.strip() if part_number else None,
        year=year,
        month=month,
        include_expired=include_expired,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/batch-delete", response_model=ApiResponse[StampingDieBatchDeleteResultVO])
def batch_delete_die_scope(
    dto: StampingDieScopeDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_DIE_LIST_DELETE)),
) -> ApiResponse[StampingDieBatchDeleteResultVO]:
    result = _die_service.delete_scope(db, dto)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_parts} 个模具零件")
