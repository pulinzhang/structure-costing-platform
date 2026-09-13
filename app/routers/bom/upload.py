"""BOM Excel 上传路由：导入时必须传 location。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.vo.bom_vo import BomImportResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom_upload_service import BomUploadService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/bom", tags=["BOM API"])

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


@router.post(
    "/upload",
    response_model=ApiResponse[BomImportResultVO],
)
async def upload_bom_excel(
    location: str = Form(..., description="采购基地（必填）"),
    vehicle_model: str = Form(..., description="项目（必填）"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.BOM_UPLOAD_UPLOAD)),
) -> ApiResponse[BomImportResultVO]:
    """导入车身件材料清单 Excel；基地+项目必选；Excel 原件落盘；同基地+车型+版本覆盖。"""
    content = await file.read()
    result = _upload_service.import_excel(
        db,
        file_content=content,
        filename=file.filename or "",
        location=location.strip(),
        vehicle_model=vehicle_model.strip(),
        current_user=current_user,
    )
    return ApiResponse.ok(data=result, message=result.message)
