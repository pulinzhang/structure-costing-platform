"""
冲压工艺上传服务

处理 Excel 解析、文件保存、简图保存、数据库存储等业务逻辑。
主数据写入使用单一大事务；进度写入辅助库。
"""

import logging
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Callable, Dict, List, Optional
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.timezone import now
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.config import settings
from app.repositories.stamping.stamping_repository import StampingPartRepository, StampingProcessRepository
from app.schemas.dto.stamping_upload_dto import FileInfo, PartData, ProcessData, UploadResult
from app.schemas.vo.user_vo import UserVO

# progress_callback(progress: int, msg: str)
ProgressCallback = Callable[[int, str], None]

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
        current_user: UserVO,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> UploadResult:
        """
        处理冲压工艺文件上传（完整业务流程）。

        主数据：删除旧数据 + 写入零件/工序在同一事务中，全部成功或全部回滚。
        """
        import tempfile
        import os

        def _report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        _report(5, "正在读取并解析 Excel...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            parse_result = parse_stamping_excel(tmp_path)
            vehicle_model = parse_result.vehicle_model or "未知车型"
            version = parse_result.version or "V1"
            stamping_supplier = parse_result.stamping_supplier or ""

            logger.info(
                "解析 Excel 完成：%d 个零件、%d 道工序",
                len(parse_result.parts),
                len(parse_result.processes),
            )
            _report(
                40,
                f"解析完成：{len(parse_result.parts)} 个零件、"
                f"{len(parse_result.processes)} 道工序，正在保存文件...",
            )

            file_info = self._save_file(
                file_content, filename, location, vehicle_model, version
            )

            _report(55, "正在保存零件简图...")
            saved_images = self._save_part_images(
                parse_result.images_by_part, file_info.upload_subdir
            )

            _report(70, "正在写入零件与工序到数据库...")
            with self.db.begin():
                part_map = self._save_parts(
                    parse_result.parts,
                    vehicle_model,
                    version,
                    file_info,
                    parse_result.images_by_part,
                    stamping_supplier,
                    filename,
                    current_user=current_user,
                )
                process_count = self._save_processes(
                    parse_result.processes, part_map, current_user=current_user
                )

                logger.info(
                    "上传处理完成: 零件 %d, 工序 %d, 简图 %d, 解析耗时 %.0fms",
                    len(part_map),
                    process_count,
                    saved_images,
                    parse_result.parse_time_ms,
                )
                _report(95, "正在提交事务...")

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
        safe_location = location.replace("/", "_").replace("\\", "_")
        safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
        safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
        timestamp_str = now().strftime("%H%M%S")
        new_filename = f"{safe_location}_{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"

        upload_subdir = settings.UPLOAD_DIR / safe_location / safe_vehicle / safe_version
        upload_subdir.mkdir(parents=True, exist_ok=True)
        file_path = upload_subdir / new_filename

        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info("文件保存成功: %s", file_path)

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
                logger.warning("保存零件简图失败 %s: %s", part_number, e)

        logger.info("零件简图落盘: %d/%d -> %s", saved, len(images_by_part), target_dir)
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
        *,
        current_user: UserVO,
    ) -> Dict[str, int]:
        """保存零件数据到数据库，返回 part_number -> part_id 映射"""
        audit = audit_create(current_user)
        self.part_repo.delete_by_vehicle_version(self.db, vehicle_model, version)
        logger.info(
            "已删除旧数据: %s %s operator=%s",
            vehicle_model,
            version,
            display_name(current_user),
        )

        parts_to_create: List[PartData] = []
        for part in parts:
            part_number = part.part_number
            if not part_number:
                continue

            sketch_url = (
                f"{file_info.safe_location}/{file_info.safe_vehicle}/"
                f"{file_info.safe_version}/{part_number}.png"
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
                excel_sheet_name=part.excel_sheet_name,
                excel_row=part.excel_row,
                excel_part_col=part.excel_part_col,
            ))

        rows = []
        for p in parts_to_create:
            d = asdict(p)
            d.update(audit)
            rows.append(d)
        self.part_repo.bulk_create(self.db, rows)
        self.db.flush()

        part_map = self.part_repo.get_id_map_by_vehicle_version(
            self.db, vehicle_model, version
        )
        logger.info("导入零件: %d 个", len(parts_to_create))
        return part_map

    def _save_processes(
        self,
        processes: List[Process],
        part_map: Dict[str, int],
        current_user: UserVO,
    ) -> int:
        """保存工序数据到数据库"""
        audit = audit_create(current_user)
        processes_to_create: List[ProcessData] = []
        part_order_counter: Dict[str, int] = {}

        for process in processes:
            part_number = process.part_number
            part_id = part_map.get(part_number)
            if not part_id:
                logger.warning(
                    "工序被跳过: part_number=%s, seq=%s",
                    part_number,
                    process.process_seq,
                )
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
            rows = []
            for p in processes_to_create:
                d = asdict(p)
                d.update(audit)
                rows.append(d)
            self.process_repo.bulk_create(self.db, rows)

        logger.info("导入工序: %d 个", len(processes_to_create))
        return len(processes_to_create)
