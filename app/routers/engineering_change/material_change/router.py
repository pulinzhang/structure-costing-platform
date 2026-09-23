"""材料变更 API。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.engineering_change.material_change import MaterialChangeUploadQueryDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.engineering_change.material_change import (
    MaterialChangeRecordVO,
    MaterialChangeUploadListRowVO,
    MaterialChangeUploadResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_PENDING,
    TASK_TYPE_ENGINEERING_CHANGE_MATERIAL_UPLOAD,
    AsyncTaskService,
)
from app.services.engineering_change.material_change.list.query import MaterialChangeQueryService
from app.services.engineering_change.material_change.list.records import list_part_records
from app.services.engineering_change.material_change.list.rollback import (
    MaterialChangeRollbackService,
)
from app.services.engineering_change.material_change.upload.service import (
    MaterialChangeUploadService,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/engineering-change/material", tags=["材料变更"])

_async_task_service = AsyncTaskService()
_upload_service = MaterialChangeUploadService()
_query_service = MaterialChangeQueryService()
_rollback_service = MaterialChangeRollbackService()


@router.get("/template")
def download_template(
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_MATERIAL_UPLOAD_UPLOAD)),
) -> StreamingResponse:
    _ = current_user
    content, filename = _upload_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/upload", response_model=ApiResponse[AsyncTaskAcceptedVO])
async def upload_material_change(
    location: str = Form(...),
    vehicle_model: str = Form(...),
    effective_year: int = Form(...),
    effective_month: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_MATERIAL_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    content = await file.read()
    result = _upload_service.start_upload(
        db,
        file_content=content,
        filename=file.filename or "material-change.xlsx",
        location=location,
        vehicle_model=vehicle_model,
        effective_year=effective_year,
        effective_month=effective_month,
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message="已提交材料变更导入任务")


@router.get(
    "/upload/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_upload_task(
    task_id: str,
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.ENGINEERING_CHANGE_MATERIAL_UPLOAD_VIEW,
            Perm.ENGINEERING_CHANGE_MATERIAL_UPLOAD_UPLOAD,
            Perm.ENGINEERING_CHANGE_MATERIAL_LIST_VIEW,
        )
    ),
) -> ApiResponse[AsyncTaskProgressVO]:
    _ = current_user
    task = _async_task_service.require_snapshot(
        task_id, TASK_TYPE_ENGINEERING_CHANGE_MATERIAL_UPLOAD
    )
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = MaterialChangeUploadResultVO.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.get(
    "/uploads",
    response_model=ApiResponse[PageResult[MaterialChangeUploadListRowVO]],
)
def list_uploads(
    query: MaterialChangeUploadQueryDTO = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_MATERIAL_LIST_VIEW)),
) -> ApiResponse[PageResult[MaterialChangeUploadListRowVO]]:
    _ = current_user
    items, total = _query_service.paginate(db, query)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条记录",
    )


@router.get("/uploads/{upload_log_id:int}/file")
def download_original(
    upload_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_MATERIAL_LIST_VIEW)),
) -> FileResponse:
    absolute_path, original_filename, media_type = _query_service.resolve_original_file(
        db, upload_log_id, current_user
    )
    encoded_name = quote(original_filename)
    return FileResponse(
        path=str(absolute_path),
        media_type=media_type,
        filename=original_filename,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.delete(
    "/uploads/{upload_log_id:int}",
    response_model=ApiResponse[None],
)
def delete_upload(
    upload_log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_MATERIAL_LIST_DELETE)),
) -> ApiResponse[None]:
    _rollback_service.rollback(db, upload_log_id, current_user)
    return ApiResponse.deleted(message="已删除材料变更")


@router.get(
    "/parts/{part_id:int}/records",
    response_model=ApiResponse[list[MaterialChangeRecordVO]],
)
def get_part_records(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PARTS_VIEW,
            Perm.ENGINEERING_CHANGE_MATERIAL_LIST_VIEW,
        )
    ),
) -> ApiResponse[list[MaterialChangeRecordVO]]:
    _ = current_user
    items = list_part_records(db, part_id)
    return ApiResponse.ok(data=items)
