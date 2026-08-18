"""
钢材基准价格 Excel 导入服务
- 源文件归档
- 解析 + 事务内 upsert
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.parsers.yishiyiyi.base_price import parse_base_price_excel
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.schemas.dto.steel_base_price_dto import SteelBasePriceWrite
from app.schemas.vo.steel_base_price_vo import SteelBasePriceImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.utils.steel_price_archive import (
    FILE_KIND_BASE_PRICE,
    save_steel_price_upload,
)

ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.steel_base_price.import")


def _base_price_write_from_record(
    record: dict[str, object],
    *,
    year: int,
    month: int,
    filename: str,
    created_by: str,
    updated_by: str,
) -> SteelBasePriceWrite:
    from decimal import Decimal

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


class SteelBasePriceImportService:
    """钢材基准价格 Excel 导入。"""

    def __init__(self) -> None:
        self.repository = SteelBasePriceRepository()

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
        current_user: UserVO,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> SteelBasePriceImportResultResponse:
        """
        解析 Excel 并执行 upsert。
        整个导入在单一事务中完成；进度写入辅助库。
        导入前先按年度/月份归档源文件，便于与政策文件成对核对。
        """
        create_audit = audit_create(current_user)

        def _report(progress: int, msg: str) -> None:
            if progress_callback:
                progress_callback(progress, msg)

        _report(5, "正在归档上传源文件...")
        save_steel_price_upload(
            file_content=file_content,
            filename=filename,
            year=year,
            month=month,
            file_kind=FILE_KIND_BASE_PRICE,
        )

        _report(10, "正在解析基准价格 Excel...")
        parse_result = parse_base_price_excel(file_content)

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
            return SteelBasePriceImportResultResponse(
                filename=filename,
                created_count=0,
                updated_count=0,
                total=0,
                warnings=parse_result.warnings,
                errors=parse_result.errors,
            )

        _report(50, f"解析完成，共 {len(writes)} 条，正在写入数据库...")
        try:
            counts = self.repository.upsert(db, writes)
            _report(90, "正在提交事务...")
            db.commit()
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
