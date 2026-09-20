"""BOM Excel 上传路由：异步任务，立即返回 task_id。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.common.permissions.codes import Perm
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.bom_vo import BomImportResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_BOM_UPLOAD,
    AsyncTaskService,
)
from app.services.bom.bom.upload.upload_service import BomUploadService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom", tags=["BOM API"])

_async_task_service = AsyncTaskService()
_upload_service = BomUploadService()


@router.get("/template")
def download_bom_import_template(
    current_user: UserVO = Depends(require_perm(Perm.BOM_UPLOAD_VIEW)),
) -> StreamingResponse:
    """下载材料清单导入模板（含三级树样例与填写说明）。"""
    content, filename = _upload_service.build_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/upload", response_model=ApiResponse[AsyncTaskAcceptedVO])
async def upload_bom_excel(
    location: str = Form(..., description="采购基地（必填）"),
    vehicle_model: str = Form(..., description="项目（必填）"),
    file: UploadFile = File(...),
    current_user: UserVO = Depends(require_perm(Perm.BOM_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """导入车身件材料清单：立即返回 task_id，后台解析入库。"""
    content = await file.read()
    accepted = BomUploadService.start_upload(
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        vehicle_model=vehicle_model.strip(),
        current_user=current_user,
    )
    return ApiResponse.ok(data=accepted, message="已提交材料清单导入任务")


@router.get(
    "/upload/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_bom_upload_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_any_perm(Perm.BOM_UPLOAD_VIEW, Perm.BOM_UPLOAD_UPLOAD)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询材料清单上传任务进度。"""
    _ = current_user
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_BOM_UPLOAD)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = BomImportResultVO.model_validate(result_raw) if result_raw else None
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )
