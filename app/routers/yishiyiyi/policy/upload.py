"""
钢价政策 Excel 上传 API
异步：立即返回 task_id，后台线程解析入库，前端轮询进度。
"""

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.common.audit import display_name
from app.common.permissions.codes import Perm
from app.database import DatabaseConfig
from app.deps.permissions import require_perm
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.steel_price_policy_vo import ImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_POLICY_UPLOAD,
    AsyncTaskService,
)
from app.services.yishiyiyi.policy import SteelPricePolicyService
from app.utils.response import ApiResponse


logger = logging.getLogger("router.steel_price_policy.upload")
router = APIRouter(prefix="/api/yishiyiyi/policy", tags=["钢价政策上传"])

_policy_service = SteelPricePolicyService()
_async_task_service = AsyncTaskService()


@router.get("/template")
def download_policy_import_template(
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载加减价政策导入模板（含样例钢种与填写说明）。"""
    content, filename = _policy_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


def _process_policy_upload_in_background(
    task_id: str,
    file_content: bytes,
    filename: str,
    year: int,
    month: int,
    current_user: UserVO,
) -> None:
    """
    后台线程执行政策 Excel 解析与入库。
    必须在独立线程中运行，禁止写成 async（否则会阻塞 Event Loop）。
    进度写入辅助库；主数据使用业务 Session 大事务。
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


@router.post(
    "/upload",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
)
async def upload_policy_excel(
    year: int = Form(..., ge=2000, le=2100, description="生效年度"),
    month: int = Form(..., ge=1, le=12, description="生效月份（1-12）"),
    file: UploadFile = File(..., description="一事一议价格 Excel 文件"),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """
    上传钢价政策 Excel，立即返回 task_id，后台线程解析入库。
    任务进度写入辅助库，不复用业务 Session。
    主数据仍在单一大事务中导入（全部成功或全部回滚）。
    """
    file_content = await file.read()

    try:
        _policy_service.validate_upload(file_content, file.filename or "")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_POLICY_UPLOAD,
        message="已提交解析队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    AsyncTaskService.submit(
        _process_policy_upload_in_background,
        task.task_id,
        file_content,
        file.filename or "policy.xlsx",
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
def get_upload_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询政策上传/解析任务进度（辅助库）"""
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_POLICY_UPLOAD:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = ImportResultResponse.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )
