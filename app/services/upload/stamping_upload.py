"""
冲压工艺上传服务
处理 Excel 解析、简图保存、数据库存储等业务逻辑
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session

from app.models import StampingPart, StampingProcess
from app.parsers import parse_stamping_excel
from app.config import settings


logger = logging.getLogger("service.stamping_upload")


class StampingUploadService:
    """冲压工艺上传服务"""

    def __init__(self, db: Session):
        self.db = db

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
        from pathlib import Path
        from datetime import datetime

        # 安全化目录名
        safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
        safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
        timestamp = datetime.now().strftime("%H%M%S")
        new_filename = f"{safe_vehicle}_{safe_version}_{timestamp}_{filename}"

        # 保存文件到磁盘
        upload_subdir = settings.UPLOAD_DIR / safe_vehicle / safe_version
        upload_subdir.mkdir(parents=True, exist_ok=True)
        file_path = upload_subdir / new_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"文件保存成功: {file_path}")

        # 解析 Excel 文件
        result = parse_stamping_excel(str(file_path))

        # 落盘零件简图
        saved_images = self._save_part_images(result.images_by_part, upload_subdir)

        # 保存零件数据
        part_map = self._save_parts(
            result.parts,
            vehicle_model,
            version,
            safe_vehicle,
            safe_version,
            result.images_by_part,
        )

        # 保存工序数据
        process_count = self._save_processes(result.processes, part_map)

        logger.info(
            f"上传处理完成: 零件 {len(part_map)}, 工序 {process_count}, "
            f"简图 {saved_images}, 解析耗时 {result.parse_time_ms:.0f}ms"
        )

        return {
            "filename": filename,
            "new_filename": new_filename,
            "size": len(file_content),
            "path": str(file_path),
            "vehicle_model": vehicle_model,
            "version": version,
            "parts_count": len(part_map),
            "processes_count": process_count,
            "images_count": saved_images,
            "warnings": result.warnings,
            "parse_time_ms": result.parse_time_ms,
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
        self.db.query(StampingProcess).filter(
            StampingProcess.part_id.in_(
                self.db.query(StampingPart.id).filter(
                    StampingPart.vehicle_model == vehicle_model,
                    StampingPart.version == version,
                )
            )
        ).delete(synchronize_session=False)
        self.db.query(StampingPart).filter(
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version,
        ).delete(synchronize_session=False)
        self.db.commit()
        logger.info(f"已删除旧数据: {vehicle_model} {version}")

        # 批量导入零件数据
        part_map: Dict[str, int] = {}
        for part_data in parts_data:
            part_number = part_data.get("part_number")
            if not part_number:
                continue

            # 先删除可能存在的旧零件（防止唯一约束冲突）
            self.db.query(StampingProcess).filter(
                StampingProcess.part_id.in_(
                    self.db.query(StampingPart.id).filter(
                        StampingPart.part_number == part_number
                    )
                )
            ).delete(synchronize_session=False)
            self.db.query(StampingPart).filter(
                StampingPart.part_number == part_number
            ).delete(synchronize_session=False)

            # 简图 URL
            sketch_url = (
                f"{safe_vehicle}/{safe_version}/{part_number}.png"
                if part_number in images_by_part
                else None
            )

            part = StampingPart(
                vehicle_model=vehicle_model,
                version=version,
                seq_no=part_data.get("seq_no"),
                part_number=part_number,
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
                sketch_url=sketch_url,
            )
            self.db.add(part)
            part_map[part_number] = part_number  # 临时占位，commit 后更新

        self.db.commit()

        # 重新查询获取真实 id
        for part in self.db.query(StampingPart).filter(
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version,
        ).all():
            if part.part_number:
                part_map[part.part_number] = part.id

        logger.info(f"导入零件: {len(parts_data)} 个, 唯一编号 {len(part_map)} 个")
        return part_map

    def _save_processes(
        self,
        processes_data: List[Dict[str, Any]],
        part_map: Dict[str, int],
    ) -> int:
        """保存工序数据到数据库"""
        process_objects = []
        skipped = 0
        # 跟踪每个零件的工序顺序
        part_order_counter: Dict[str, int] = {}

        for proc_data in processes_data:
            part_number = proc_data.get("part_number")
            part_id = part_map.get(part_number)
            if not part_id:
                skipped += 1
                continue

            # 每个零件的工序顺序从1开始
            order = part_order_counter.get(part_number, 0) + 1
            part_order_counter[part_number] = order

            process = StampingProcess(
                part_id=part_id,
                process_seq=proc_data.get("process_seq"),
                process_order=order,
                process_code=proc_data.get("process_code"),
                die_sets=proc_data.get("die_sets"),
                tonnage=proc_data.get("tonnage"),
                remark=proc_data.get("remark"),
            )
            process_objects.append(process)

        self.db.add_all(process_objects)
        self.db.commit()

        logger.info(
            f"导入工序: {len(process_objects)} 个"
            + (f" (跳过 {skipped} 个孤儿工序)" if skipped else "")
        )
        return len(process_objects)
