"""
钢材基准价格 Excel 导入服务
- 源文件归档
- 解析 + 事务内 upsert
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.steel_grade_category import as_canonical_category
from app.exceptions import BusinessException
from app.parsers.yishiyiyi.base_price import parse_base_price_excel
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.schemas.dto.steel_base_price_dto import SteelBasePriceWrite
from app.schemas.vo.steel_base_price_vo import SteelBasePriceImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
from app.services.yishiyiyi.base_price.importing.template_builder import (
    build_steel_base_price_template,
)
from app.utils.steel_price_archive import (
    FILE_KIND_BASE_PRICE,
    save_steel_price_upload,
)

ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.steel_base_price.import")


# 钢厂名不得为纯数字（含小数），防止列错位把价格读进钢厂
_NUMERIC_STEEL_MILL_RE = re.compile(r"^[+-]?\d+(\.\d+)?$")


def _is_numeric_steel_mill(steel_mill: object) -> bool:
    """钢厂值为纯数字（或可解析为数字）时视为格式错误。"""
    if isinstance(steel_mill, int | float | Decimal):
        return True
    text = str(steel_mill).strip()
    if not text:
        return False
    if _NUMERIC_STEEL_MILL_RE.fullmatch(text):
        return True
    try:
        Decimal(text)
        return True
    except (InvalidOperation, ValueError):
        return False


def _assert_steel_mills_not_numeric(records: list[dict[str, object]]) -> None:
    """导入小锁：任一钢厂为数字则整批拒绝，避免列错位脏数据入库。"""
    bad_samples: list[str] = []
    bad_count = 0
    for record in records:
        mill = record.get("steel_mill")
        if not _is_numeric_steel_mill(mill):
            continue
        bad_count += 1
        if len(bad_samples) >= 5:
            continue
        excel_row = record.get("excel_row")
        location = record.get("location")
        bad_samples.append(f"第{excel_row}行/{location}基地→钢厂「{mill}」")
    if bad_count == 0:
        return
    sample_text = "；".join(bad_samples)
    more = f"等共 {bad_count} 处" if bad_count > len(bad_samples) else f"共 {bad_count} 处"
    raise BusinessException(
        f"钢厂不能为数字（疑似表格列错位或格式不正确）：{sample_text}（{more}）。"
        "请核对各基地「中标钢厂」列是否对齐后再导入。"
    )


def _base_price_write_from_record(
    record: dict[str, object],
    *,
    year: int,
    month: int,
    filename: str,
    created_by: str,
    updated_by: str,
) -> SteelBasePriceWrite:
    thick = record.get("thick")
    width = record.get("width")
    base_price = record["base_price"]
    processing_fee = record.get("processing_fee")
    if not isinstance(base_price, Decimal):
        base_price = Decimal(str(base_price))
    if processing_fee is None:
        processing_fee = Decimal("0")
    elif not isinstance(processing_fee, Decimal):
        processing_fee = Decimal(str(processing_fee))
    if thick is not None and not isinstance(thick, Decimal):
        thick = Decimal(str(thick))
    if width is not None and not isinstance(width, Decimal):
        width = Decimal(str(width))
    excel_row_raw = record["excel_row"]
    excel_col_raw = record.get("excel_col")
    excel_row = int(str(excel_row_raw)) if excel_row_raw is not None else 0
    excel_col = int(str(excel_col_raw)) if excel_col_raw is not None else None
    return SteelBasePriceWrite(
        year=year,
        month=month,
        location=str(record["location"]),
        steel_mill=str(record["steel_mill"]),
        category_name=str(record["category_name"]),
        grade=str(record["grade"]),
        thick=thick if isinstance(thick, Decimal) or thick is None else Decimal(str(thick)),
        width=width if isinstance(width, Decimal) or width is None else Decimal(str(width)),
        base_price=base_price,
        processing_fee=processing_fee,
        excel_filename=filename,
        sheet_name=str(record["sheet_name"]),
        excel_row=excel_row,
        spec=str(record["spec"]) if record.get("spec") is not None else None,
        excel_col=excel_col,
        remark=str(record["remark"]) if record.get("remark") is not None else None,
        created_by=created_by,
        updated_by=updated_by,
    )


def _canonicalize_grade_and_category(db: Session, writes: list[SteelBasePriceWrite]) -> list[str]:
    """每条直接问主数据；落库用档案 grade 与档案大类。空牌号视为脏数据，整批拒绝。"""
    empty_rows = [write.excel_row for write in writes if not (write.grade or "").strip()]
    if empty_rows:
        sample = "、".join(str(row) for row in empty_rows[:10])
        extra = f"，共 {len(empty_rows)} 行" if len(empty_rows) > 10 else ""
        raise BusinessException(f"牌号不能为空（Excel 第{sample}行{extra}）")
    service = SteelGradeCategoryService()
    matched = service.require_matched_grades(db, [write.grade for write in writes])
    warnings: list[str] = []
    seen_mismatch: set[tuple[str, str, str]] = set()
    for write in writes:
        key = write.grade.strip()
        archive = matched[key]
        excel_category = as_canonical_category(write.category_name)
        if excel_category and excel_category != archive.category_name:
            seen_mismatch.add((write.grade, write.category_name, archive.category_name))
        write.grade = archive.grade
        write.category_name = archive.category_name
    for raw_grade, excel_category, archive_category in sorted(seen_mismatch):
        warnings.append(
            f"牌号「{raw_grade}」表头钢种「{excel_category}」已按档案改为「{archive_category}」"
        )
    return warnings


class SteelBasePriceImportService:
    """钢材基准价格 Excel 导入。"""

    def __init__(self) -> None:
        self.repository = SteelBasePriceRepository()

    def build_template(self) -> tuple[bytes, str]:
        """下载用基准价格导入模板（含样例宽表）。"""
        return build_steel_base_price_template()

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
        carry_mills: dict[tuple[str, str], str] | None = None,
    ) -> SteelBasePriceImportResultResponse:
        """
        解析 Excel 并执行 upsert。
        整个导入在单一事务中完成；进度写入辅助库。
        导入前先按年度/月份归档源文件，便于与政策文件成对核对。
        carry_mills：仅价格列时按 (基地, 牌号) 承接上月中标钢厂。
        """
        create_audit = audit_create(current_user)

        def _report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        _report(5, "正在归档上传源文件...")
        archive_path = save_steel_price_upload(
            file_content=file_content,
            filename=filename,
            year=year,
            month=month,
            file_kind=FILE_KIND_BASE_PRICE,
        )
        stored_relpath = to_upload_relpath(archive_path)

        _report(10, "正在解析基准价格 Excel...")
        location_service = LocationService()
        lookup = location_service.enabled_name_lookup(db)
        if not lookup:
            raise BusinessException("没有已启用基地，请到基地页手工增加或启用（#/location）")
        parse_result = parse_base_price_excel(
            file_content,
            location_lookup=lookup,
            carry_mills=carry_mills,
        )
        _assert_steel_mills_not_numeric(parse_result.records)
        # lookup 只过滤宽表列；落库仍走写入门禁。
        unique_locations = {
            str(record.get("location") or "").strip()
            for record in parse_result.records
            if str(record.get("location") or "").strip()
        }
        for name in unique_locations:
            location_service.require_enabled(db, name)

        writes = [
            _base_price_write_from_record(
                record,
                year=year,
                month=month,
                filename=filename,
                created_by=create_audit["created_by"],
                updated_by=create_audit["updated_by"],
            )
            for record in parse_result.records
        ]
        if not writes:
            _report(100, "解析完成，无有效数据行")
            try:
                register_existing(
                    db,
                    file_category="steel_base_price",
                    stored_relpath=stored_relpath,
                    original_filename=filename,
                    current_user=current_user,
                    year=year,
                    month=month,
                )
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("登记基准价源文件失败: filename=%s", filename)
                raise
            return SteelBasePriceImportResultResponse(
                filename=filename,
                created_count=0,
                updated_count=0,
                total=0,
                warnings=parse_result.warnings,
                errors=parse_result.errors,
            )

        grade_warnings = _canonicalize_grade_and_category(db, writes)
        parse_result.warnings.extend(grade_warnings)
        _report(50, f"解析完成，共 {len(writes)} 条，正在写入数据库...")
        try:
            counts = self.repository.upsert(db, writes)
            register_existing(
                db,
                file_category="steel_base_price",
                stored_relpath=stored_relpath,
                original_filename=filename,
                current_user=current_user,
                year=year,
                month=month,
            )
            _report(90, "正在提交事务...")
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                "基准价格写入失败。牌号必须已在「主数据 → 牌号分类」，"
                "且同年月、基地、钢厂、牌号、规格不能重复。"
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("导入基准价格失败: filename=%s", filename)
            raise

        logger.info(
            "导入基准价格完成: filename=%s, created=%d, updated=%d",
            filename,
            counts["created"],
            counts["updated"],
        )

        return SteelBasePriceImportResultResponse(
            filename=filename,
            created_count=counts["created"],
            updated_count=counts["updated"],
            total=counts["created"] + counts["updated"],
            warnings=parse_result.warnings,
            errors=parse_result.errors,
        )
