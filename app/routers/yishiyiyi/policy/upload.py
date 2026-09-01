"""
钢价政策 Excel 上传 API
异步：立即返回 task_id，后台线程解析入库，前端轮询进度。
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.common.permissions.codes import Perm
from app.deps.permissions import require_perm
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.steel_price_policy_vo import ImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_POLICY_UPLOAD,
    AsyncTaskService,
)
from app.services.yishiyiyi.policy import SteelPricePolicyService
from app.utils.response import ApiResponse

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
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


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
    _policy_service.validate_upload(file_content, file.filename or "")

    accepted = _policy_service.start_upload(
        file_content=file_content,
        filename=file.filename or "policy.xlsx",
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
)
def get_upload_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_POLICY_UPLOAD_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询政策上传/解析任务进度（辅助库）"""
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_POLICY_UPLOAD)

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = ImportResultResponse.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )
