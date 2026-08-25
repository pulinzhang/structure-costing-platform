"""
冲压工艺文件上传路由
异步任务：立即返回 task_id，后台线程解析入库，前端轮询进度。
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from urllib.parse import quote

from app.common.permissions.codes import Perm
from app.utils.logging_config import get_logger
from app.deps.permissions import require_perm
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_STAMPING_UPLOAD,
    AsyncTaskService,
)
from app.services.stamping.upload import StampingUploadService
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.utils.response import ApiResponse


logger = get_logger("router.stamping.upload")
router = APIRouter(prefix="/api/stamping/upload", tags=["冲压工艺上传 API"])

_async_task_service = AsyncTaskService()


@router.get("/template")
def download_stamping_import_template(
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载冲压工艺导入模板（含样例零件与填写说明）。"""
    content, filename = StampingUploadService.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@router.post("/", response_model=ApiResponse[AsyncTaskAcceptedVO])
async def upload_stamping_file(
    location: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """上传车型冲压工艺文件，立即返回 task_id，后台解析入库。"""
    logger.info(
        "接收到车型冲压工艺文件上传: 基地=%s, 文件=%s",
        location,
        file.filename,
    )

    content = await file.read()
    accepted = StampingUploadService.start_upload(
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        current_user=current_user,
    )
    return ApiResponse.ok(
        data=accepted,
        message="上传成功，后台开始解析",
    )


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_stamping_upload_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询冲压工艺上传任务进度。"""
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_STAMPING_UPLOAD)

    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=AsyncTaskService.parse_result_json(task.get("result_json")),
        ),
    )
