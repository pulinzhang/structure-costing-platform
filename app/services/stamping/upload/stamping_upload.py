"""
冲压工艺上传服务

处理 Excel 解析、文件保存、简图保存、数据库存储等业务逻辑。
主数据写入使用单一大事务；进度写入辅助库。
"""

import logging
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.timezone import now
from app.common.upload_scope_validation import validate_stamping_process_upload_scope
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.models.tailor_weld import TailorWeldAssemblyParsed
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.parsers.stamping.tailor_weld_parser import parse_tailor_weld_excel
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_upload_dto import FileInfo, PartData, ProcessData, UploadResult
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_STAMPING_UPLOAD,
    AsyncTaskService,
    WorkerTaskOutcome,
)
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.stamping.process_seq_validator import (
    ProcessSeqOccurrence,
    find_duplicate_process_seqs,
    format_duplicate_process_seq_issues,
)
from app.services.stamping.tailor_weld_blank_service import StampingTailorWeldBlankService
from app.services.stamping.upload.cost_ratio_preserver import ProcessCostRatioPreserver
from app.services.stamping.upload.swing_shear_resolver import collect_swing_shear_part_numbers
from app.services.stamping.upload.template_builder import build_stamping_process_template
from app.services.yishiyiyi.steel_grade_category import (
    SOURCE_STAMPING_UPLOAD,
    GradeEnsureItem,
    SteelGradeCategoryService,
)

# progress_callback(progress: int, msg: str)
ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.stamping_upload")


class StampingUploadService:
    """冲压工艺上传服务"""

    def __init__(self, db: Session):
        self.db = db
        self.part_repo = StampingPartRepository()
        self.process_repo = StampingProcessRepository()
        self.cost_ratio_preserver = ProcessCostRatioPreserver()
        self.tailor_weld_service = StampingTailorWeldBlankService()

    @staticmethod
    def build_template() -> tuple[bytes, str]:
        """下载用冲压工艺导入模板（含样例零件）。"""
        return build_stamping_process_template()

    def process_upload(
        self,
        file_content: bytes,
        filename: str,
        location: str,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
    ) -> UploadResult:
        """
        处理冲压工艺文件上传（完整业务流程）。

        主数据：解析完成后用库中已设比率回写工序，再删除旧数据并写入；
        删除与写入在同一事务中，全部成功或全部回滚。
        """
        import os
        import tempfile

        def _report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        _report(5, "正在读取并解析 Excel...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            parse_result = parse_stamping_excel(tmp_path)
            tailor_result = parse_tailor_weld_excel(tmp_path)
            scope = validate_stamping_process_upload_scope(
                location=location,
                stamping_supplier=parse_result.stamping_supplier,
                vehicle_model=parse_result.vehicle_model,
                version=parse_result.version,
            )
            location = scope.location
            vehicle_model = scope.vehicle_model
            version = scope.version
            stamping_supplier = scope.stamping_supplier
            tailor_parent_numbers = set(tailor_result.parent_part_numbers)

            duplicate_seqs = find_duplicate_process_seqs(
                [
                    ProcessSeqOccurrence(
                        part_number=process.part_number,
                        process_seq=process.process_seq,
                        excel_row=process.excel_row,
                    )
                    for process in parse_result.processes
                ]
            )
            if duplicate_seqs:
                raise BusinessException(
                    format_duplicate_process_seq_issues(duplicate_seqs, source_name="工艺确认表")
                )

            logger.info(
                "解析 Excel 完成：%d 个零件、%d 道工序、%d 个拼焊总成",
                len(parse_result.parts),
                len(parse_result.processes),
                tailor_result.assembly_count,
            )
            _report(
                40,
                f"解析完成：{len(parse_result.parts)} 个零件、"
                f"{len(parse_result.processes)} 道工序、"
                f"{tailor_result.assembly_count} 个拼焊件，正在保存文件...",
            )

            file_info = self._save_file(file_content, filename, location, vehicle_model, version)

            _report(55, "正在保存零件简图...")
            saved_images = self._save_part_images(
                parse_result.images_by_part, file_info.upload_subdir
            )

            _report(70, "正在写入零件、工序与拼焊子片到数据库...")
            with self.db.begin():
                existing_processes = self.process_repo.list_by_scope(
                    self.db,
                    location=file_info.safe_location,
                    stamping_supplier=stamping_supplier,
                    vehicle_model=vehicle_model,
                    version=version,
                )
                self.cost_ratio_preserver.apply(
                    parse_result.processes,
                    existing_processes,
                    parse_result.parts,
                )
                part_map = self._save_parts(
                    parse_result.parts,
                    vehicle_model,
                    version,
                    file_info,
                    parse_result.images_by_part,
                    stamping_supplier,
                    filename,
                    tailor_parent_numbers=tailor_parent_numbers,
                    swing_shear_part_numbers=collect_swing_shear_part_numbers(
                        parse_result.parts,
                        parse_result.processes,
                    ),
                    current_user=current_user,
                )
                tailor_assemblies, tailor_blanks, tailor_warnings = (
                    self.tailor_weld_service.save_parsed_for_upload(
                        self.db,
                        tailor_result.assemblies,
                        part_map,
                        current_user,
                    )
                )
                process_count = self._save_processes(
                    parse_result.processes, part_map, current_user=current_user
                )
                grade_result = SteelGradeCategoryService().ensure_grades(
                    self.db,
                    self._collect_upload_grades(parse_result.parts, tailor_result.assemblies),
                    source=SOURCE_STAMPING_UPLOAD,
                    current_user=current_user,
                )

                warnings = list(parse_result.warnings) + list(tailor_result.warnings)
                warnings.extend(tailor_warnings)
                if grade_result.conflicts:
                    warnings.extend(grade_result.conflicts)
                parse_time_ms = parse_result.parse_time_ms + tailor_result.parse_time_ms

                logger.info(
                    "上传处理完成: 零件 %d, 工序 %d, 简图 %d, 拼焊 %d/%d, 解析耗时 %.0fms",
                    len(part_map),
                    process_count,
                    saved_images,
                    tailor_assemblies,
                    tailor_blanks,
                    parse_time_ms,
                )
                _report(95, "正在提交事务...")

                register_existing(
                    self.db,
                    file_category="stamping_process",
                    stored_relpath=to_upload_relpath(file_info.file_path),
                    original_filename=filename,
                    current_user=current_user,
                    location=file_info.safe_location,
                    vehicle_model=vehicle_model,
                    process_version=version,
                    stamping_supplier=stamping_supplier or None,
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
                    tailor_weld_assembly_count=tailor_assemblies,
                    tailor_weld_blank_count=tailor_blanks,
                    warnings=warnings,
                    parse_time_ms=parse_time_ms,
                )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    def _collect_upload_grades(
        parts: list[Part],
        assemblies: list[TailorWeldAssemblyParsed],
    ) -> list[GradeEnsureItem]:
        seen: set[str] = set()
        items: list[GradeEnsureItem] = []

        def add_material(raw: str | None) -> None:
            grade = (raw or "").strip()
            if not grade or grade in seen:
                return
            seen.add(grade)
            items.append(GradeEnsureItem(grade=grade))

        for part in parts:
            add_material(part.material)
        for assembly in assemblies:
            add_material(assembly.material)
            for blank in assembly.blanks:
                add_material(blank.material)
        return items

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
        images_by_part: dict[str, bytes],
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
                c if c.isalnum() or c in ("_", "-") else "_" for c in str(part_number)
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
        parts: list[Part],
        vehicle_model: str,
        version: str,
        file_info: FileInfo,
        images_by_part: dict[str, bytes],
        stamping_supplier: str = "",
        excel_filename: str = "",
        tailor_parent_numbers: set[str] | None = None,
        swing_shear_part_numbers: set[str] | None = None,
        *,
        current_user: UserVO,
    ) -> dict[str, int]:
        """保存零件数据到数据库，返回 part_number -> part_id 映射"""
        audit = audit_create(current_user)
        tailor_parents = tailor_parent_numbers or set()
        swing_shear_parts = swing_shear_part_numbers or set()
        location = file_info.safe_location
        self.part_repo.delete_by_scope(
            self.db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        logger.info(
            "已删除旧数据: %s/%s/%s/%s operator=%s",
            location,
            stamping_supplier,
            vehicle_model,
            version,
            display_name(current_user),
        )

        parts_to_create: list[PartData] = []
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

            parts_to_create.append(
                PartData(
                    location=location,
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
                    is_offal_nested=part.is_offal_nested,
                    offal_source=part.offal_source,
                    is_scrap_byproduct=part.is_scrap_byproduct,
                    has_swing_shear=part_number in swing_shear_parts,
                    die_type=part.die_type,
                    process_method=part.process_method,
                    automation=part.automation,
                    remark=part.remark,
                    sketch_url=sketch_url,
                    is_tailor_welded=part_number in tailor_parents,
                    excel_filename=excel_filename,
                    excel_sheet_name=part.excel_sheet_name,
                    excel_row=part.excel_row,
                    excel_part_col=part.excel_part_col,
                )
            )

        audit = audit_create(current_user)
        for part_row in parts_to_create:
            part_row.created_by = audit["created_by"]
            part_row.updated_by = audit["updated_by"]
        self.part_repo.bulk_create(self.db, parts_to_create)
        self.db.flush()

        part_map = self.part_repo.get_id_map_by_scope(
            self.db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        logger.info("导入零件: %d 个", len(parts_to_create))
        return part_map

    def _save_processes(
        self,
        processes: list[Process],
        part_map: dict[str, int],
        current_user: UserVO,
    ) -> int:
        """保存工序数据到数据库"""
        audit = audit_create(current_user)
        processes_to_create: list[ProcessData] = []
        part_order_counter: dict[str, int] = {}

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

            processes_to_create.append(
                ProcessData(
                    part_id=part_id,
                    process_seq=process.process_seq,
                    process_order=order,
                    process_code=process.process_code,
                    die_sets=process.die_sets,
                    die_number=process.die_number,
                    tonnage=process.tonnage,
                    cost_ratio=process.cost_ratio
                    if process.cost_ratio is not None
                    else Decimal("1.00"),
                    remark=process.remark,
                )
            )

        if processes_to_create:
            for process_row in processes_to_create:
                process_row.created_by = audit["created_by"]
                process_row.updated_by = audit["updated_by"]
            self.process_repo.bulk_create(self.db, processes_to_create)

        logger.info("导入工序: %d 个", len(processes_to_create))
        return len(processes_to_create)

    @classmethod
    def start_upload(
        cls,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        """创建异步任务并入队；后台线程开独立 Session 解析入库。"""
        location = (location or "").strip()
        if not location:
            raise BusinessException("请输入基地")
        if not filename:
            raise BusinessException("未提供文件名")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in {".xlsx", ".xls"}:
            raise BusinessException(f"不支持的文件类型: {ext}，仅支持 .xlsx / .xls")
        if not file_content:
            raise BusinessException("上传文件为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise BusinessException(
                f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )

        from dataclasses import asdict

        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STAMPING_UPLOAD,
            message="已提交解析队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            service = cls(db)
            try:
                result = service.process_upload(
                    file_content=file_content,
                    filename=filename,
                    location=location,
                    progress_callback=on_progress,
                    current_user=current_user,
                )
            except (BusinessException, ValueError) as error:
                logger.warning("冲压上传业务失败: task_id=%s error=%s", task.task_id, error)
                return WorkerTaskOutcome(
                    status=STATUS_FAILED,
                    progress=0,
                    message=str(error),
                )
            return WorkerTaskOutcome(
                status=STATUS_COMPLETED,
                message=(
                    f"上传成功：{result.parts_count} 个零件，"
                    f"{result.processes_count} 道工序"
                    f"（拼焊 {result.tailor_weld_assembly_count} 件 / "
                    f"{result.tailor_weld_blank_count} 片）"
                ),
                result=asdict(result),
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始解析...",
            work=work,
            crash_message=lambda error: f"解析异常: {error}",
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)
