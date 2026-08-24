"""BOM Excel 导入服务：解析入库，Excel 原件与简图落盘（防扯皮）。"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.upload_scope_validation import validate_bom_material_upload_scope
from app.common.timezone import now
from app.config import settings
from app.parsers.bom.bom_parser import BomParsedNode, parse_bom_excel
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite
from app.schemas.vo.bom_vo import BomImportResultVO, BomSnapshotVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom_template_builder import build_bom_material_template
from app.services.file_trace.register import register_existing

logger = logging.getLogger("service.bom.upload")

# Excel 列号（1-based）：各层级「零件号」列，与 node_parser 一致
_EXCEL_PART_COL_BY_LEVEL = {0: 3, 1: 9, 2: 14}


class BomUploadService:
    """BOM Excel 导入：必须指定基地；Excel + 简图必须落盘。"""

    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self.node_repo = BomNodeRepository()

    def build_template(self) -> tuple[bytes, str]:
        """下载用材料清单导入模板（含三级树样例）。"""
        return build_bom_material_template()

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        current_user: UserVO,
    ) -> BomImportResultVO:
        location = (location or "").strip()
        if not location:
            raise ValueError("请选择采购基地")

        original_name = Path(filename).name
        ext = Path(original_name).suffix.lower()
        if ext not in {".xlsx", ".xls"}:
            raise ValueError("仅支持 .xlsx / .xls 文件")
        if not file_content:
            raise ValueError("文件内容为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise ValueError(
                f"文件过大，上限 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )

        parse_result = parse_bom_excel(file_content)
        meta = parse_result.meta
        if not parse_result.nodes:
            raise ValueError("未解析到 BOM 节点，请检查 Excel 格式")

        scope = validate_bom_material_upload_scope(
            location=location,
            vehicle_model=meta.vehicle_model,
            bom_version=meta.bom_version,
        )
        location = scope.location
        vehicle_model = scope.vehicle_model
        bom_version = scope.bom_version
        file_hash = hashlib.sha256(file_content).hexdigest()
        relative_path = self._save_excel_file(
            file_content=file_content,
            filename=original_name,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        sketch_dir_rel = self._sketch_dir_relative(location, vehicle_model, bom_version)
        saved_images = self._save_node_sketches(
            parse_result.nodes,
            sketch_dir_rel=sketch_dir_rel,
        )

        replaced = False
        try:
            existing = self.snapshot_repo.get_by_unique_key(
                db, location, vehicle_model, bom_version
            )
            if existing:
                self.snapshot_repo.delete(db, existing)
                replaced = True

            audit = audit_create(current_user)
            snapshot = self.snapshot_repo.create(
                db,
                BomSnapshotWrite(
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    product_category=meta.product_category,
                    customer_name=meta.customer_name,
                    stage=meta.stage or "initial",
                    doc_no=meta.doc_no,
                    prepare_dept=meta.prepare_dept,
                    doc_date=meta.doc_date,
                    revision_date=meta.revision_date,
                    title=meta.title,
                    source_filename=original_name,
                    source_sheet_name=parse_result.sheet_name,
                    source_file_path=relative_path,
                    source_file_hash=file_hash,
                    status="active",
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
            )

            sheet_name = parse_result.sheet_name
            index_to_id: dict[int, int] = {}
            for index, parsed in enumerate(parse_result.nodes):
                parent_id = None
                if parsed.parent_index is not None:
                    parent_id = index_to_id.get(parsed.parent_index)
                    if parent_id is None:
                        raise ValueError(
                            f"节点父子关系异常: {parsed.part_number} "
                            f"parent_index={parsed.parent_index}"
                        )

                row = self.node_repo.create(
                    db,
                    BomNodeWrite(
                        snapshot_id=snapshot.id,
                        parent_id=parent_id,
                        level=parsed.level,
                        sort_no=parsed.sort_no,
                        seq_no=parsed.seq_no,
                        internal_number=parsed.internal_number,
                        part_number=parsed.part_number,
                        part_name=parsed.part_name,
                        qty=parsed.qty,
                        qty_unit=parsed.qty_unit or "pcs",
                        qty_text=parsed.qty_text,
                        node_role=parsed.node_role,
                        is_supply_unit=bool(parsed.is_supply_unit),
                        material=parsed.material,
                        thickness_mm=parsed.thickness_mm,
                        thickness_text=parsed.thickness_text,
                        material_mill=parsed.material_mill,
                        part_weight=parsed.part_weight,
                        gauge_developed=parsed.gauge_developed,
                        weld_info=parsed.weld_info,
                        remark=parsed.remark,
                        sketch_url=saved_images.get(index),
                        excel_filename=original_name,
                        excel_sheet_name=sheet_name,
                        excel_row=parsed.source_row,
                        excel_part_col=_EXCEL_PART_COL_BY_LEVEL.get(parsed.level),
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    )
                )
                index_to_id[index] = row.id

            register_existing(
                db,
                file_category="bom_material",
                stored_relpath=relative_path,
                original_filename=original_name,
                current_user=current_user,
                file_hash=file_hash,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                business_ref_type="bom_snapshot",
                business_ref_id=snapshot.id,
            )

            db.commit()
            db.refresh(snapshot)
        except Exception:
            db.rollback()
            raise

        vo = BomSnapshotVO.model_validate(snapshot)
        vo.node_count = len(parse_result.nodes)
        image_count = len(saved_images)
        message = (
            f"{'覆盖导入' if replaced else '导入'}成功："
            f"{vehicle_model} / {bom_version} / {location}，"
            f"{len(parse_result.nodes)} 个节点，{image_count} 张简图"
        )
        logger.info("%s file=%s hash=%s", message, relative_path, file_hash[:12])
        return BomImportResultVO(
            snapshot=vo,
            node_count=len(parse_result.nodes),
            image_count=image_count,
            replaced=replaced,
            message=message,
        )

    def _save_excel_file(
        self,
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
        safe_location = self._safe_segment(location)
        safe_vehicle = self._safe_segment(vehicle_model)
        safe_version = self._safe_segment(bom_version)
        timestamp_str = now().strftime("%Y%m%d_%H%M%S")
        stored_name = (
            f"{safe_location}_{safe_vehicle}_{safe_version}_{timestamp_str}_{filename}"
        )

        relative_dir = Path("bom") / safe_location / safe_vehicle / safe_version
        absolute_dir = settings.UPLOAD_DIR / relative_dir
        absolute_dir.mkdir(parents=True, exist_ok=True)

        absolute_path = absolute_dir / stored_name
        with open(absolute_path, "wb") as file_obj:
            file_obj.write(file_content)

        relative_path = str(relative_dir / stored_name).replace("\\", "/")
        logger.info("BOM Excel 已落盘: %s (%s bytes)", absolute_path, len(file_content))
        return relative_path

    def _sketch_dir_relative(
        self, location: str, vehicle_model: str, bom_version: str
    ) -> str:
        safe_location = self._safe_segment(location)
        safe_vehicle = self._safe_segment(vehicle_model)
        safe_version = self._safe_segment(bom_version)
        return str(
            Path("bom") / safe_location / safe_vehicle / safe_version / "sketches"
        ).replace("\\", "/")

    def _save_node_sketches(
        self,
        nodes: list[BomParsedNode],
        *,
        sketch_dir_rel: str,
    ) -> dict[int, str]:
        """
        将节点简图保存为 PNG，返回 node_index -> sketch_url（相对 UPLOAD_DIR）。
        URL 形如 bom/青岛/T28/D_00/sketches/12_501006875AA.png，可通过 /uploads/ 访问。
        """
        target_dir = settings.UPLOAD_DIR / sketch_dir_rel
        target_dir.mkdir(parents=True, exist_ok=True)

        saved: dict[int, str] = {}
        for index, node in enumerate(nodes):
            if not node.sketch_bytes:
                continue
            safe_part = "".join(
                ch if ch.isalnum() or ch in ("_", "-") else "_"
                for ch in str(node.part_number or f"node{index}")
            ) or f"node{index}"
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
            sum(1 for n in nodes if n.sketch_bytes),
            target_dir,
        )
        return saved

    @staticmethod
    def _safe_segment(value: str) -> str:
        text = (value or "").strip() or "unknown"
        for ch in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", " "):
            text = text.replace(ch, "_")
        return text
