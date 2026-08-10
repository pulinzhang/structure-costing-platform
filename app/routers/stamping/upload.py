"""
冲压工艺文件上传路由
前后端分离 API 接口
"""

import logging

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.config import settings
from app.database import get_db
from app.services.stamping.upload import StampingUploadService
from app.schemas.vo.stamping_upload_vo import UploadResultVO
from app.utils.response import ApiResponse


logger = get_logger("router.stamping.upload")
router = APIRouter(prefix="/api/stamping/upload", tags=["冲压工艺上传 API"])


@router.post("/", response_model=ApiResponse[UploadResultVO])
async def upload_stamping_file(
    location: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ApiResponse[UploadResultVO]:
    """上传车型冲压工艺文件，解析并保存到数据库"""
    logger.info(
        f"接收到车型冲压工艺文件上传: 基地={location}, 文件={file.filename}"
    )

    if not location.strip():
        raise HTTPException(status_code=400, detail="请输入基地")
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
            location=location,
        )
        return ApiResponse.ok(
            data=UploadResultVO(
                filename=result.filename,
                new_filename=result.new_filename,
                size=result.size,
                path=result.path,
                location=result.location,
                vehicle_model=result.vehicle_model,
                version=result.version,
                parts_count=result.parts_count,
                processes_count=result.processes_count,
                images_count=result.images_count,
                warnings=result.warnings,
                parse_time_ms=result.parse_time_ms,
            ),
            message=f"上传成功: {result.parts_count} 个零件, {result.processes_count} 道工序"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")
