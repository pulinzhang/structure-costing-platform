"""工程变更上传 API。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.engineering_change.design_change import EngineeringChangeUploadResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_PENDING,
    TASK_TYPE_ENGINEERING_CHANGE_UPLOAD,
    AsyncTaskService,
)
from app.services.engineering_change.design_change.upload.service import (
    EngineeringChangeUploadService,
)
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/engineering-change", tags=["工程变更"])

_async_task_service = AsyncTaskService()
_upload_service = EngineeringChangeUploadService()


@router.get("/template", summary="下载设计变更导入模板")
def download_template(
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_UPLOAD_UPLOAD)),
) -> StreamingResponse:
    _ = current_user
    content, filename = _upload_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/upload", response_model=ApiResponse[AsyncTaskAcceptedVO], summary="上传设计变更")
async def upload_engineering_change(
    location: str = Form(...),
    vehicle_model: str = Form(...),
    effective_year: int = Form(...),
    effective_month: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ENGINEERING_CHANGE_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    content = await file.read()
    result = _upload_service.start_upload(
        db,
        file_content=content,
        filename=file.filename or "engineering-change.xlsx",
        location=location,
        vehicle_model=vehicle_model,
        effective_year=effective_year,
        effective_month=effective_month,
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message="已提交工程变更导入任务")


@router.get(
    "/upload/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
    summary="查询设计变更上传进度",
)
def get_upload_task(
    task_id: str,
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.ENGINEERING_CHANGE_UPLOAD_VIEW,
            Perm.ENGINEERING_CHANGE_UPLOAD_UPLOAD,
            Perm.ENGINEERING_CHANGE_ORDER_LIST_VIEW,
        )
    ),
) -> ApiResponse[AsyncTaskProgressVO]:
    _ = current_user
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_ENGINEERING_CHANGE_UPLOAD)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = EngineeringChangeUploadResultVO.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )
