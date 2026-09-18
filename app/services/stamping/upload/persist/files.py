"""冲压工艺 Excel 与零件简图落盘。"""

from __future__ import annotations

import logging
from pathlib import Path

from app.common.timezone import now
from app.config import settings
from app.schemas.dto.stamping_upload_dto import FileInfo

logger = logging.getLogger("service.stamping_upload")


def save_file(
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    version: str,
) -> FileInfo:
    """保存上传文件到磁盘，返回文件信息。"""
    safe_location = location.replace("/", "_").replace("\\", "_")
    safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
    safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
    timestamp_str = now().strftime("%H%M%S")
    new_filename = f"{safe_location}_{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"

    upload_subdir = settings.UPLOAD_DIR / safe_location / safe_vehicle / safe_version
    upload_subdir.mkdir(parents=True, exist_ok=True)
    file_path = upload_subdir / new_filename

    with open(file_path, "wb") as file_obj:
        file_obj.write(file_content)

    logger.info("文件保存成功: %s", file_path)

    return FileInfo(
        file_path=str(file_path),
        new_filename=new_filename,
        safe_location=safe_location,
        safe_vehicle=safe_vehicle,
        safe_version=safe_version,
        upload_subdir=str(upload_subdir),
    )


def save_part_images(
    images_by_part: dict[str, bytes],
    target_dir: str,
) -> int:
    """保存零件简图到磁盘。"""
    if not images_by_part:
        return 0

    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    saved = 0
    for part_number, img_bytes in images_by_part.items():
        if not part_number or not img_bytes:
            continue
        safe_name = "".join(
            char if char.isalnum() or char in ("_", "-") else "_" for char in str(part_number)
        )
        if not safe_name:
            continue
        img_path = target_path / f"{safe_name}.png"
        try:
            with open(img_path, "wb") as file_obj:
                file_obj.write(img_bytes)
            saved += 1
        except OSError as error:
            logger.warning("保存零件简图失败 %s: %s", part_number, error)

    logger.info("零件简图落盘: %d/%d -> %s", saved, len(images_by_part), target_dir)
    return saved
