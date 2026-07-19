"""
冲压工艺上传服务
处理 Excel 解析、文件保存、简图保存、数据库存储等业务逻辑
"""

import logging
from pathlib import Path
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.config import settings
from app.repositories.stamping.stamping_repository import StampingPartRepository, StampingProcessRepository


logger = logging.getLogger("service.stamping_upload")


class StampingUploadService:
    """冲压工艺上传服务"""

    def __init__(self, db: Session):
        self.db = db
        self.part_repo = StampingPartRepository()
        self.process_repo = StampingProcessRepository()

    def process_upload(
        self,
        file_content: bytes,
        filename: str,
        vehicle_model: str,
        version: str,
    ) -> Dict[str, Any]:
        """
        处理冲压工艺文件上传（完整业务流程）

        Args:
            file_content: 文件二进制内容
            filename: 原始文件名
            vehicle_model: 车型
            version: 版本

        Returns:
            处理结果字典
        """

        # 1. 保存文件到磁盘
        file_info = self._save_file(file_content, filename, vehicle_model, version)
        upload_subdir = file_info["upload_subdir"]

        # 2. 解析 Excel 文件
        parse_result = parse_stamping_excel(file_info["file_path"])

        # 3. 落盘零件简图
        saved_images = self._save_part_images(parse_result.images_by_part, upload_subdir)

        # 4. 保存零件数据到数据库
        part_map = self._save_parts(
            parse_result.parts,
            vehicle_model,
            version,
            file_info["safe_vehicle"],
            file_info["safe_version"],
            parse_result.images_by_part,
        )

        # 5. 保存工序数据到数据库
        process_count = self._save_processes(parse_result.processes, part_map)

        logger.info(
            f"上传处理完成: 零件 {len(part_map)}, 工序 {process_count}, "
            f"简图 {saved_images}, 解析耗时 {parse_result.parse_time_ms:.0f}ms"
        )

        return {
            "filename": filename,
            "new_filename": file_info["new_filename"],
            "size": len(file_content),
            "path": file_info["file_path"],
            "vehicle_model": vehicle_model,
            "version": version,
            "parts_count": len(part_map),
            "processes_count": process_count,
            "images_count": saved_images,
            "warnings": parse_result.warnings,
            "parse_time_ms": parse_result.parse_time_ms,
        }

    def _save_file(
        self,
        file_content: bytes,
        filename: str,
        vehicle_model: str,
        version: str,
    ) -> Dict[str, Any]:
        """保存上传文件到磁盘，返回文件信息"""
        import datetime

        safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
        safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
        timestamp_str = datetime.datetime.now().strftime("%H%M%S")
        new_filename = f"{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"

        upload_subdir = settings.UPLOAD_DIR / safe_vehicle / safe_version
        upload_subdir.mkdir(parents=True, exist_ok=True)
        file_path = upload_subdir / new_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"文件保存成功: {file_path}")

        return {
            "file_path": str(file_path),
            "new_filename": new_filename,
            "safe_vehicle": safe_vehicle,
            "safe_version": safe_version,
            "upload_subdir": upload_subdir,
        }

    def _save_part_images(
        self,
        images_by_part: Dict[str, bytes],
        target_dir: Path,
    ) -> int:
        """保存零件简图到磁盘"""
        if not images_by_part:
            return 0

        target_dir.mkdir(parents=True, exist_ok=True)
        saved = 0
        for part_number, img_bytes in images_by_part.items():
            if not part_number or not img_bytes:
                continue
            safe_name = "".join(
                c if c.isalnum() or c in ("_", "-") else "_"
                for c in str(part_number)
            )
            if not safe_name:
                continue
            img_path = target_dir / f"{safe_name}.png"
            try:
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                saved += 1
            except Exception as e:
                logger.warning(f"保存零件简图失败 {part_number}: {e}")

        logger.info(f"零件简图落盘: {saved}/{len(images_by_part)} -> {target_dir}")
        return saved

    def _save_parts(
        self,
        parts_data: List[Dict[str, Any]],
        vehicle_model: str,
        version: str,
        safe_vehicle: str,
        safe_version: str,
        images_by_part: Dict[str, bytes],
    ) -> Dict[str, int]:
        """保存零件数据到数据库，返回 part_number -> part_id 映射"""
        # 删除同车型同版本的旧数据
        self.part_repo.delete_by_vehicle_version(self.db, vehicle_model, version)
        logger.info(f"已删除旧数据: {vehicle_model} {version}")

        # 批量创建零件
        parts_to_create = []
        for part_data in parts_data:
            part_number = part_data.get("part_number")
            if not part_number:
                continue

            sketch_url = (
                f"{safe_vehicle}/{safe_version}/{part_number}.png"
                if part_number in images_by_part
                else None
            )

            parts_to_create.append({
                "vehicle_model": vehicle_model,
                "version": version,
                "seq_no": part_data.get("seq_no"),
                "part_number": part_number,
                "part_name": part_data.get("part_name"),
                "material": part_data.get("material"),
                "thickness": part_data.get("thickness"),
                "part_weight": part_data.get("part_weight"),
                "sheet_length": part_data.get("sheet_length"),
                "sheet_width": part_data.get("sheet_width"),
                "parts_per_sheet": part_data.get("parts_per_sheet"),
                "sheet_type": part_data.get("sheet_type"),
                "tonnage": part_data.get("tonnage"),
                "die_type": part_data.get("die_type"),
                "process_method": part_data.get("process_method"),
                "automation": part_data.get("automation"),
                "remark": part_data.get("remark"),
                "sketch_url": sketch_url,
            })

        self.part_repo.bulk_create(self.db, parts_to_create)

        # 获取 ID 映射
        part_map = self.part_repo.get_id_map_by_vehicle_version(
            self.db, vehicle_model, version
        )
        logger.info(f"导入零件: {len(parts_to_create)} 个")
        return part_map

    def _save_processes(
        self,
        processes_data: List[Dict[str, Any]],
        part_map: Dict[str, int],
    ) -> int:
        """保存工序数据到数据库"""
        processes_to_create = []
        part_order_counter: Dict[str, int] = {}

        for proc_data in processes_data:
            part_number = proc_data.get("part_number")
            part_id = part_map.get(part_number)
            if not part_id:
                continue

            order = part_order_counter.get(part_number, 0) + 1
            part_order_counter[part_number] = order

            processes_to_create.append({
                "part_id": part_id,
                "process_seq": proc_data.get("process_seq"),
                "process_order": order,
                "process_code": proc_data.get("process_code"),
                "die_sets": proc_data.get("die_sets"),
                "tonnage": proc_data.get("tonnage"),
                "remark": proc_data.get("remark"),
            })

        if processes_to_create:
            self.process_repo.bulk_create(self.db, processes_to_create)

        logger.info(f"导入工序: {len(processes_to_create)} 个")
        return len(processes_to_create)
