"""
上传路由
Upload Router
"""

import logging
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse

from app.utils.logging_config import get_logger
from app.config import settings


logger = get_logger("router.upload")
router = APIRouter(prefix="/upload", tags=["Upload"])


@router.get("/", response_class=HTMLResponse, name="upload.index")
async def index(request: Request):
    """
    上传页面
    """
    logger.info("访问上传页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "title": "上传",
        }
    )


@router.post("/", name="upload.handle")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件接口
    """
    logger.info(f"接收到文件上传: {file.filename}")

    # 验证文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = "." + file.filename.split(".")[-1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，支持的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 验证文件大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
        )

    # 保存文件
    file_path = settings.UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"文件保存成功: {file_path}")

    return {
        "success": True,
        "filename": file.filename,
        "size": len(content),
        "path": str(file_path),
    }
