"""
冲压工艺文件上传路由
"""

import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.config import settings
from app.database import get_db
from app.services.stamping.upload import StampingUploadService
from app.utils.response import ApiResponse


logger = get_logger("router.stamping.upload")
router = APIRouter(prefix="/stamping/upload", tags=["Stamping Upload"])


@router.get("/", name="stamping.upload.index")
async def upload_index():
    """重定向到上传页面"""
    return RedirectResponse(url="/stamping/upload/page", status_code=302)


@router.get("/page", name="stamping.upload_page", response_class=HTMLResponse)
async def upload_page(request: Request):
    """冲压工艺文件上传页面"""
    return request.app.state.templates.TemplateResponse("stamping/upload.html", {"request": request})


@router.post("/", name="stamping.upload")
async def upload_stamping_file(
    vehicle_model: str = Form(...),
    version: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传车型冲压工艺文件，解析并保存到数据库"""
    logger.info(
        f"接收到车型冲压工艺文件上传: 车型={vehicle_model}, "
        f"版本={version}, 文件={file.filename}"
    )

    if not vehicle_model.strip():
        raise HTTPException(status_code=400, detail="请输入车型")
    if not version.strip():
        raise HTTPException(status_code=400, detail="请输入版本")
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = "." + file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
        )

    try:
        service = StampingUploadService(db)
        result = service.process_upload(
            file_content=content,
            filename=file.filename,
            vehicle_model=vehicle_model,
            version=version,
        )
        return ApiResponse.success(
            data=result,
            message=f"上传成功: {result['parts_count']} 个零件, {result['processes_count']} 道工序"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")
