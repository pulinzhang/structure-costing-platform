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
from app.common.period import previous_month
from app.common.steel_grade_category import as_canonical_category
from app.exceptions import BusinessException
from app.parsers.yishiyiyi.base_price.steel_base_price_parser import (
    parse_base_price_excel,
)
from app.repositories.yishiyiyi.base_price.steel_base_price_repository import (
    SteelBasePriceRepository,
)
from app.schemas.dto.steel_base_price_dto import SteelBasePriceWrite
from app.schemas.vo.steel_base_price_vo import SteelBasePriceImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.steel_grade_category.service import (
    SteelGradeCategoryService,
)
from app.services.masterdata.steel_mill.normalize import normalize_mill_text
from app.services.masterdata.steel_mill.service import SteelMillService
from app.services.settings.system.service import SettingsService
from app.services.yishiyiyi.base_price.gate import (
    AwardLine,
    reject_excessive_month_moves,
    reject_invalid_base_price_award,
    reject_processing_fee_over_limit,
    sample_text,
    unexpected_reference_width_warnings,
)
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


def _award_from_write(write: SteelBasePriceWrite) -> AwardLine:
    return AwardLine(
        location=write.location,
        grade=write.grade,
        steel_mill=write.steel_mill,
        thick=write.thick,
        width=write.width,
        category_name=write.category_name,
        processing_fee=write.processing_fee,
        base_price=write.base_price,
        excel_row=write.excel_row,
    )


def _reject_invalid_award(
    db: Session,
    repository: SteelBasePriceRepository,
    writes: list[SteelBasePriceWrite],
    incoming: list[AwardLine],
) -> None:
    """同一年月、基地、牌号只能有一个中标钢厂；参考规格不合法则整批拒绝，不写库。"""
    if not writes:
        return
    stored = repository.list_by_year_month(db, year=writes[0].year, month=writes[0].month)
    reject_invalid_base_price_award(
        incoming,
        [
            AwardLine(
                location=row.location,
                grade=row.grade,
                steel_mill=row.steel_mill,
                thick=row.thick,
                width=row.width,
            )
            for row in stored
        ],
        max_thickness=SettingsService().get_body_panel_max_thickness(db),
    )


def _reject_excessive_month_moves(
    db: Session,
    repository: SteelBasePriceRepository,
    writes: list[SteelBasePriceWrite],
    incoming: list[AwardLine],
) -> None:
    """上月同一参考规格的单价加加工费超出设置范围则整批拒绝，不写库。"""
    if not writes:
        return
    prev_year, prev_month = previous_month(writes[0].year, writes[0].month)
    previous_rows = repository.list_by_year_month(db, year=prev_year, month=prev_month)
    previous = [
        AwardLine(
            location=row.location,
            grade=row.grade,
            steel_mill=row.steel_mill,
            thick=row.thick,
            width=row.width,
            base_price=row.base_price,
            processing_fee=row.processing_fee,
        )
        for row in previous_rows
    ]
    limit = SettingsService().get_base_price_month_move_limit(db)
    reject_excessive_month_moves(incoming, previous, limit=limit)


def _raise_if_processing_fee_rejected(errors: list[str]) -> None:
    """加工费缺列或单元格不是数字时整批拒绝，避免把旁边的价格或默认金额写进去。"""
    fee_errors = [item for item in errors if "加工费" in item]
    if fee_errors:
        raise BusinessException("；".join(fee_errors))


def _assert_steel_mills_not_numeric(records: list[dict[str, object]]) -> None:
    """导入小锁：任一钢厂为数字则整批拒绝，避免列错位脏数据入库。"""
    bad_samples: list[str] = []
    for record in records:
        mill = record.get("steel_mill")
        if not _is_numeric_steel_mill(mill):
            continue
        excel_row = record.get("excel_row")
        location = record.get("location")
        bad_samples.append(f"第{excel_row}行/{location}基地→钢厂「{mill}」")
    if not bad_samples:
        return
    raise BusinessException(
        "钢厂不能为数字（疑似表格列错位或格式不正确）："
        + sample_text(bad_samples)
        + "。请核对各基地「中标钢厂」列是否对齐后再导入。"
    )


def _base_price_mill_place(record: dict[str, object]) -> str:
    """拒绝句里的位置：基准价 Excel 行。解析行始终带行号。"""
    return f"基准价，Excel 第{record['excel_row']}行"


def _base_price_write_from_record(
    record: dict[str, object],
    *,
    year: int,
    month: int,
    filename: str,
    created_by: str,
    updated_by: str,
    steel_mill_id: int,
    canonical_steel_mill: str,
) -> SteelBasePriceWrite:
    thick = record.get("thick")
    width = record.get("width")
    base_price = record["base_price"]
    processing_fee = record.get("processing_fee")
    if not isinstance(base_price, Decimal):
        base_price = Decimal(str(base_price))
    if processing_fee is None:
        raise BusinessException("加工费缺失，不能导入")
    if not isinstance(processing_fee, Decimal):
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
        steel_mill_id=steel_mill_id,
        canonical_steel_mill=canonical_steel_mill,
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


def _reject_collapsed_mill_keys(writes: list[SteelBasePriceWrite]) -> None:
    """牌号收口之后，两种原文收到同一钢厂且业务键相同则整本退回。"""
    seen: dict[tuple[object, ...], str] = {}
    for write in writes:
        text = normalize_mill_text(write.steel_mill)
        key = (
            write.year,
            write.month,
            write.location,
            write.steel_mill_id,
            write.category_name,
            write.grade,
            write.thick,
            write.width,
        )
        previous = seen.get(key)
        if previous is not None and previous != text:
            raise BusinessException(
                f"「{previous}」与「{text}」收到同一钢厂，业务键相撞。本文件未写入。"
            )
        seen[key] = text


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
        _raise_if_processing_fee_rejected(parse_result.errors)
        _assert_steel_mills_not_numeric(parse_result.records)
        # lookup 只过滤宽表列；落库仍走写入门禁。
        unique_locations = {
            str(record.get("location") or "").strip()
            for record in parse_result.records
            if str(record.get("location") or "").strip()
        }
        for name in unique_locations:
            location_service.require_enabled(db, name)

        mill_hits = SteelMillService().require_enabled_many(
            db,
            [str(record.get("steel_mill") or "") for record in parse_result.records],
            places=[_base_price_mill_place(record) for record in parse_result.records],
        )
        writes: list[SteelBasePriceWrite] = []
        for record in parse_result.records:
            hit = mill_hits[normalize_mill_text(str(record.get("steel_mill") or ""))]
            writes.append(
                _base_price_write_from_record(
                    record,
                    year=year,
                    month=month,
                    filename=filename,
                    created_by=create_audit["created_by"],
                    updated_by=create_audit["updated_by"],
                    steel_mill_id=hit.id,
                    canonical_steel_mill=hit.full_name,
                )
            )
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
        incoming = [_award_from_write(write) for write in writes]
        reject_processing_fee_over_limit(
            incoming,
            limit=SettingsService().get_base_price_processing_fee_limit(db),
        )
        width_warnings = unexpected_reference_width_warnings(incoming)
        _reject_invalid_award(db, self.repository, writes, incoming)
        _reject_excessive_month_moves(db, self.repository, writes, incoming)
        _report(50, f"解析完成，共 {len(writes)} 条，正在写入数据库...")
        try:
            _reject_collapsed_mill_keys(writes)
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
            width_warnings=width_warnings,
        )
