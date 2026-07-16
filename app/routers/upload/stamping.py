"""
车型冲压工艺文件上传路由
Stamping Process Upload Router
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.config import settings
from app.database import get_db
from app.models import StampingPart, StampingProcess
from app.parsers import parse_stamping_excel


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
    logger.info(f"接收到车型冲压工艺文件上传: 车型={vehicle_model}, 版本={version}, 文件={file.filename}")

    # 验证输入
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

    # 读取文件内容
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
        )

    # 保存文件
    today = datetime.now().strftime("%Y%m%d")
    safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
    safe_version = version.replace("/", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%H%M%S")
    new_filename = f"{safe_vehicle}_{safe_version}_{timestamp}_{file.filename}"

    upload_subdir = settings.UPLOAD_DIR / safe_vehicle / today
    upload_subdir.mkdir(parents=True, exist_ok=True)
    file_path = upload_subdir / new_filename

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"文件保存成功: {file_path}")

    try:
        # 解析 Excel 文件
        parts_data, processes_data = parse_stamping_excel(str(file_path))
        logger.info(f"解析完成: {len(parts_data)} 个零件, {len(processes_data)} 道工序")

        # 删除同车型同版本的旧数据
        db.query(StampingProcess).filter(
            StampingProcess.part_id.in_(
                db.query(StampingPart.id).filter(
                    StampingPart.vehicle_model == vehicle_model,
                    StampingPart.version == version
                )
            )
        ).delete(synchronize_session=False)
        db.query(StampingPart).filter(
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version
        ).delete(synchronize_session=False)
        db.commit()

        # 导入零件数据
        part_map: Dict[str, int] = {}  # part_number -> part_id
        for part_data in parts_data:
            part = StampingPart(
                vehicle_model=vehicle_model,
                version=version,
                seq_no=part_data.get("seq_no"),
                part_number=part_data.get("part_number"),
                part_name=part_data.get("part_name"),
                material=part_data.get("material"),
                thickness=part_data.get("thickness"),
                part_weight=part_data.get("part_weight"),
                sheet_length=part_data.get("sheet_length"),
                sheet_width=part_data.get("sheet_width"),
                parts_per_sheet=part_data.get("parts_per_sheet"),
                sheet_type=part_data.get("sheet_type"),
                tonnage=part_data.get("tonnage"),
                die_type=part_data.get("die_type"),
                process_method=part_data.get("process_method"),
                automation=part_data.get("automation"),
                remark=part_data.get("remark"),
            )
            db.add(part)
            db.commit()
            db.refresh(part)
            part_map[part.part_number] = part.id

        # 导入工序数据
        process_count = 0
        for proc_data in processes_data:
            part_number = proc_data.get("part_number")
            part_id = part_map.get(part_number)
            if not part_id:
                logger.warning(f"工序数据找不到对应零件: {part_number}")
                continue

            process = StampingProcess(
                part_id=part_id,
                process_seq=proc_data.get("process_seq"),
                process_code=proc_data.get("process_code"),
                die_sets=proc_data.get("die_sets"),
                tonnage=proc_data.get("tonnage"),
                remark=proc_data.get("remark"),
            )
            db.add(process)
            process_count += 1

        db.commit()

        return JSONResponse({
            "success": True,
            "message": f"上传成功: {len(parts_data)} 个零件, {process_count} 道工序",
            "data": {
                "filename": file.filename,
                "new_filename": new_filename,
                "size": len(content),
                "path": str(file_path),
                "vehicle_model": vehicle_model,
                "version": version,
                "parts_count": len(parts_data),
                "processes_count": process_count,
            }
        })

    except Exception as e:
        logger.error(f"处理文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")
