"""
冲压工艺文件上传路由
异步任务：立即返回 task_id，后台线程解析入库，前端轮询进度。
"""

from dataclasses import asdict

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.utils.logging_config import get_logger
from app.config import settings
from app.database import DatabaseConfig
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


def _process_stamping_upload_in_background(
    task_id: str,
    file_content: bytes,
    filename: str,
    location: str,
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
        )
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_COMPLETED,
            progress=100,
            message=(
                f"上传成功：{result.parts_count} 个零件，"
                f"{result.processes_count} 道工序"
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
    )
    AsyncTaskService.submit(
        _process_stamping_upload_in_background,
        task.task_id,
        content,
        file.filename,
        location.strip(),
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
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询冲压工艺上传任务进度。"""
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_STAMPING_UPLOAD:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    result = AsyncTaskService.parse_result_json(task.get("result_json"))
    updated_at_value = task.get("updated_at")
    updated_at = (
        updated_at_value.timestamp()
        if hasattr(updated_at_value, "timestamp")
        else float(updated_at_value or 0)
    )

    return ApiResponse.ok(
        data=AsyncTaskProgressVO(
            status=task.get("status") or STATUS_PENDING,
            progress=int(task.get("progress") or 0),
            msg=task.get("message") or "",
            result=result,
            updated_at=updated_at,
        ),
    )
