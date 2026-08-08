"""
冲压工艺上传服务

处理 Excel 解析、文件保存、简图保存、数据库存储等业务逻辑
"""

import logging
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Dict, List
from sqlalchemy.orm import Session

from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.config import settings
from app.repositories.stamping.stamping_repository import StampingPartRepository, StampingProcessRepository
from app.schemas.dto.stamping_upload_dto import FileInfo, PartData, ProcessData, UploadResult


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
        location: str,
    ) -> UploadResult:
        """
        处理冲压工艺文件上传（完整业务流程）

        Args:
            file_content: 文件二进制内容
            filename: 原始文件名
            location: 采购基地，例：大连、芜湖、鄂尔多斯、青岛

        Returns:
            UploadResult 处理结果
        """
        import tempfile
        import os

        # 1. 先保存到临时文件，解析 Excel 获取车型版本
        with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            # 2. 解析 Excel 文件获取车型版本
            parse_result = parse_stamping_excel(tmp_path)
            vehicle_model = parse_result.vehicle_model or "未知车型"
            version = parse_result.version or "V1"
            stamping_supplier = parse_result.stamping_supplier or ""

            logger.info("解析 Excel 完成：%d 个零件、%d 道工序", len(parse_result.parts), len(parse_result.processes))

            # 3. 用 location + 车型版本保存文件到正式路径
            file_info = self._save_file(file_content, filename, location, vehicle_model, version)

            # 4. 落盘零件简图（文件系统操作，事务外）
            saved_images = self._save_part_images(parse_result.images_by_part, file_info.upload_subdir)

            # 5-6. 数据库操作在事务中执行（原子性保证）
            with self.db.begin():
                # 5. 保存零件数据到数据库
                part_map = self._save_parts(
                    parse_result.parts,
                    vehicle_model,
                    version,
                    file_info,
                    parse_result.images_by_part,
                    stamping_supplier,
                    filename,
                )

                # 6. 保存工序数据到数据库
                process_count = self._save_processes(parse_result.processes, part_map)

                logger.info(
                    f"上传处理完成: 零件 {len(part_map)}, 工序 {process_count}, "
                    f"简图 {saved_images}, 解析耗时 {parse_result.parse_time_ms:.0f}ms"
                )

                return UploadResult(
                    filename=filename,
                    new_filename=file_info.new_filename,
                    size=len(file_content),
                    path=file_info.file_path,
                    location=location,
                    vehicle_model=vehicle_model,
                    version=version,
                    parts_count=len(part_map),
                    processes_count=process_count,
                    images_count=saved_images,
                    warnings=parse_result.warnings,
                    parse_time_ms=parse_result.parse_time_ms,
                )
        finally:
            # 删除临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _save_file(
        self,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        version: str,
    ) -> FileInfo:
        """保存上传文件到磁盘，返回文件信息"""
        import datetime

        safe_location = location.replace("/", "_").replace("\\", "_")
        safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
        safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
        timestamp_str = datetime.datetime.now().strftime("%H%M%S")
        new_filename = f"{safe_location}_{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"

        upload_subdir = settings.UPLOAD_DIR / safe_location / safe_vehicle / safe_version
        upload_subdir.mkdir(parents=True, exist_ok=True)
        file_path = upload_subdir / new_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"文件保存成功: {file_path}")

        return FileInfo(
            file_path=str(file_path),
            new_filename=new_filename,
            safe_location=safe_location,
            safe_vehicle=safe_vehicle,
            safe_version=safe_version,
            upload_subdir=str(upload_subdir),
        )

    def _save_part_images(
        self,
        images_by_part: Dict[str, bytes],
        target_dir: str,
    ) -> int:
        """保存零件简图到磁盘"""
        if not images_by_part:
            return 0

        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
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
            img_path = target_path / f"{safe_name}.png"
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
        parts: List[Part],
        vehicle_model: str,
        version: str,
        file_info: FileInfo,
        images_by_part: Dict[str, bytes],
        stamping_supplier: str = "",
        excel_filename: str = "",
    ) -> Dict[str, int]:
        """保存零件数据到数据库，返回 part_number -> part_id 映射"""
        # 删除同车型同版本的旧数据
        self.part_repo.delete_by_vehicle_version(self.db, vehicle_model, version)
        logger.info(f"已删除旧数据: {vehicle_model} {version}")

        # 批量创建零件
        parts_to_create: List[PartData] = []
        for part in parts:
            part_number = part.part_number
            if not part_number:
                continue

            sketch_url = (
                f"{file_info.safe_location}/{file_info.safe_vehicle}/{file_info.safe_version}/{part_number}.png"
                if part_number in images_by_part
                else None
            )

            parts_to_create.append(PartData(
                location=file_info.safe_location,
                vehicle_model=vehicle_model,
                version=version,
                stamping_supplier=stamping_supplier,
                seq_no=part.seq_no,
                part_number=part_number,
                part_name=part.part_name,
                material=part.material,
                thickness=part.thickness,
                part_weight=part.part_weight,
                sheet_length=part.sheet_length,
                sheet_width=part.sheet_width,
                parts_per_sheet=part.parts_per_sheet,
                sheet_type=part.sheet_type,
                die_type=part.die_type,
                process_method=part.process_method,
                automation=part.automation,
                remark=part.remark,
                sketch_url=sketch_url,
                excel_filename=excel_filename,
            ))

        self.part_repo.bulk_create(self.db, [asdict(p) for p in parts_to_create])
        # flush 确保数据落库，后续查询可看到新插入的记录
        self.db.flush()

        # 获取 ID 映射
        part_map = self.part_repo.get_id_map_by_vehicle_version(
            self.db, vehicle_model, version
        )
        logger.info(f"导入零件: {len(parts_to_create)} 个")
        return part_map

    def _save_processes(
        self,
        processes: List[Process],
        part_map: Dict[str, int],
    ) -> int:
        """保存工序数据到数据库"""
        processes_to_create: List[ProcessData] = []
        part_order_counter: Dict[str, int] = {}

        for process in processes:
            part_number = process.part_number
            part_id = part_map.get(part_number)
            if not part_id:
                logger.warning("工序被跳过: part_number=%s, seq=%s", part_number, process.process_seq)
                continue

            order = part_order_counter.get(part_number, 0) + 1
            part_order_counter[part_number] = order

            processes_to_create.append(ProcessData(
                part_id=part_id,
                process_seq=process.process_seq,
                process_order=order,
                process_code=process.process_code,
                die_sets=process.die_sets,
                tonnage=process.tonnage,
                cost_ratio=Decimal("1.00"),
                remark=process.remark,
            ))

        if processes_to_create:
            self.process_repo.bulk_create(self.db, [asdict(p) for p in processes_to_create])

        logger.info("导入工序: %d 个", len(processes_to_create))
        return len(processes_to_create)