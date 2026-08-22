"""
冲压工艺文件上传路由
异步任务：立即返回 task_id，后台线程解析入库，前端轮询进度。
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from urllib.parse import quote

from app.common.permissions.codes import Perm
from app.utils.logging_config import get_logger
from app.config import settings
from app.database import DatabaseConfig
from app.common.audit import display_name
from app.deps.permissions import require_perm
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
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


def _process_stamping_upload_in_background(
    task_id: str,
    file_content: bytes,
    filename: str,
    location: str,
    current_user: UserVO,
) -> None:
    """后台线程解析冲压工艺 Excel；独立 Session，不复用请求 db。"""
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
        service = StampingUploadService(db)
        result = service.process_upload(
            file_content=file_content,
            filename=filename,
            location=location,
            progress_callback=on_progress,
            current_user=current_user,
        )
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_COMPLETED,
            progress=100,
            message=(
                f"上传成功：{result.parts_count} 个零件，"
                f"{result.processes_count} 道工序"
                f"（拼焊 {result.tailor_weld_assembly_count} 件 / "
                f"{result.tailor_weld_blank_count} 片）"
            ),
            result=asdict(result),
        )
    except ValueError as error:
        logger.warning("冲压上传业务失败: task_id=%s error=%s", task_id, error)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=str(error),
        )
    except Exception as error:
        logger.exception("冲压上传异常: task_id=%s filename=%s", task_id, filename)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=f"解析异常: {error}",
        )
    finally:
        db.close()


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

    if not location.strip():
        raise HTTPException(status_code=400, detail="请输入基地")
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = "." + file.filename.split(".")[-1].lower()
    allowed = {".xlsx", ".xls"}
    if ext not in allowed:
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
        task_type=TASK_TYPE_STAMPING_UPLOAD,
        message="已提交解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    AsyncTaskService.submit(
        _process_stamping_upload_in_background,
        task.task_id,
        content,
        file.filename,
        location.strip(),
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
def get_stamping_upload_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询冲压工艺上传任务进度。"""
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_STAMPING_UPLOAD:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=AsyncTaskService.parse_result_json(task.get("result_json")),
        ),
    )
