"""
钢材基准价格 Excel 导入服务
- 源文件归档
- 解析 + 事务内 upsert
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.parsers.yishiyiyi.base_price import parse_base_price_excel
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.schemas.vo.steel_base_price_vo import SteelBasePriceImportResultResponse
from app.schemas.vo.user_vo import UserVO
from app.utils.steel_price_archive import (
    FILE_KIND_BASE_PRICE,
    save_steel_price_upload,
)

ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.steel_base_price.import")


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
        update_audit = audit_update(current_user)

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

        for record in parse_result.records:
            record["excel_filename"] = filename
            record["year"] = year
            record["month"] = month
            # insert 用 created_by+updated_by；update 仅取 updated_by（repo allowlist）
            record.update(create_audit)
            record.update(update_audit)
        if not parse_result.records:
            _report(100, "解析完成，无有效数据行")
            return SteelBasePriceImportResultResponse(
                filename=filename,
                created_count=0,
                updated_count=0,
                total=0,
                warnings=parse_result.warnings,
                errors=parse_result.errors,
            )

        _report(50, f"解析完成，共 {len(parse_result.records)} 条，正在写入数据库...")
        try:
            counts = self.repository.upsert(db, parse_result.records)
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
