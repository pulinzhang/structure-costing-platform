"""材料清单 Excel 与节点简图落盘。"""

from __future__ import annotations

import logging
from pathlib import Path

from app.common.timezone import now
from app.config import settings
from app.parsers.bom.models import BomParsedNode

logger = logging.getLogger("service.bom.upload")


def save_excel_file(
    *,
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> str:
    """
    保存 Excel 到 uploads/bom/{基地}/{车型}/{版本}/，返回相对 UPLOAD_DIR 的路径。
    文件名带时间戳，覆盖导入时仍保留历史原件。
    """
    safe_location = _safe_segment(location)
    safe_vehicle = _safe_segment(vehicle_model)
    safe_version = _safe_segment(bom_version)
    timestamp_str = now().strftime("%Y%m%d_%H%M%S")
    stored_name = f"{safe_location}_{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"

    relative_dir = Path("bom") / safe_location / safe_vehicle / safe_version
    absolute_dir = settings.UPLOAD_DIR / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    absolute_path = absolute_dir / stored_name
    with open(absolute_path, "wb") as file_obj:
        file_obj.write(file_content)

    relative_path = str(relative_dir / stored_name).replace("\\", "/")
    logger.info("BOM Excel 已落盘: %s (%s bytes)", absolute_path, len(file_content))
    return relative_path


def save_node_sketches(
    nodes: list[BomParsedNode],
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> dict[int, str]:
    """
    将节点简图保存为 PNG，返回 node_index -> sketch_url（相对 UPLOAD_DIR）。
    URL 形如 bom/青岛/T28/D_00/sketches/12_501006875AA.png，可通过 /uploads/ 访问。
    """
    sketch_dir_rel = _sketch_dir_relative(location, vehicle_model, bom_version)
    target_dir = settings.UPLOAD_DIR / sketch_dir_rel
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[int, str] = {}
    for index, node in enumerate(nodes):
        if not node.sketch_bytes:
            continue
        safe_part = (
            "".join(
                ch if ch.isalnum() or ch in ("_", "-") else "_"
                for ch in str(node.part_number or f"node{index}")
            )
            or f"node{index}"
        )
        file_name = f"{node.sort_no}_{safe_part}.png"
        abs_path = target_dir / file_name
        try:
            with open(abs_path, "wb") as file_obj:
                file_obj.write(node.sketch_bytes)
        except OSError as exc:
            logger.warning("保存 BOM 简图失败 %s: %s", file_name, exc)
            continue
        saved[index] = f"{sketch_dir_rel}/{file_name}".replace("\\", "/")

    logger.info(
        "BOM 简图落盘: %s/%s -> %s",
        len(saved),
        sum(1 for node in nodes if node.sketch_bytes),
        target_dir,
    )
    return saved


def _sketch_dir_relative(location: str, vehicle_model: str, bom_version: str) -> str:
    safe_location = _safe_segment(location)
    safe_vehicle = _safe_segment(vehicle_model)
    safe_version = _safe_segment(bom_version)
    return str(Path("bom") / safe_location / safe_vehicle / safe_version / "sketches").replace(
        "\\", "/"
    )


def _safe_segment(value: str) -> str:
    text = (value or "").strip() or "unknown"
    for ch in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", " "):
        text = text.replace(ch, "_")
    return text
