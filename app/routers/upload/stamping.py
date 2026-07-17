"""
车型冲压工艺文件上传路由
Stamping Process Upload Router
"""

import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.config import settings
from app.database import get_db
from app.services.upload.stamping_upload import StampingUploadService


logger = get_logger("router.stamping")
router = APIRouter(prefix="/upload/stamping", tags=["Stamping Upload"])


@router.get("/", response_class=HTMLResponse, name="stamping.index")
async def index(request: Request):
    """车型冲压工艺文件上传页面"""
    logger.info("访问车型冲压工艺文件上传页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "upload/stamping.html",
        {"request": request, "title": "车型冲压工艺文件上传"}
    )


@router.post("/", name="stamping.upload")
async def upload_stamping_file(
    vehicle_model: str = Form(...),
    version: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传车型冲压工艺文件，解析并保存到数据库

    Args:
        vehicle_model: 车型
        version: 版本
        file: Excel 文件
        db: 数据库会话
    """
    logger.info(
        f"接收到车型冲压工艺文件上传: 车型={vehicle_model}, "
        f"版本={version}, 文件={file.filename}"
    )

    # 验证输入（HTTP 层职责）
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

    # 读取并验证文件大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
        )

    try:
        # 调用 service 处理所有业务逻辑
        service = StampingUploadService(db)
        result = service.process_upload(
            file_content=content,
            filename=file.filename,
            vehicle_model=vehicle_model,
            version=version,
        )

        return JSONResponse({
            "success": True,
            "message": f"上传成功: {result['parts_count']} 个零件",
            "data": result,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")
