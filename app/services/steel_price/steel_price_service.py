"""钢材价格业务服务。"""

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.parsers.steel_price import parse_steel_price_excel
from app.repositories.steel_price import SteelPriceRepository
from app.schemas.dto.steel_price_dto import (
    SteelPriceCreate,
    SteelPriceQuery,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceResponse,
    SteelPriceImportResultResponse,
)


logger = logging.getLogger("service.steel_price")


class SteelPriceService:
    """钢材价格查询与导入业务。"""

    def __init__(self) -> None:
        self.repository = SteelPriceRepository()

    def paginate(
        self, db: Session, query: SteelPriceQuery
    ) -> tuple[list[SteelPriceResponse], int, dict[str, list[str]]]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate(
            db,
            year=query.year,
            month=query.month,
            steel_type=query.steel_type.strip() if query.steel_type else None,
            grade=query.grade.strip() if query.grade else None,
            steel_mill=query.steel_mill.strip() if query.steel_mill else None,
            skip=skip,
            limit=query.size,
        )
        rows = [SteelPriceResponse.model_validate(record) for record in records]
        return rows, total, self.repository.get_filter_options(db)

    def get_by_id(self, db: Session, record_id: int) -> Optional[SteelPriceResponse]:
        """获取单条记录。"""
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None
        return SteelPriceResponse.model_validate(record)

    def create(
        self, db: Session, data: SteelPriceCreate
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        """创建钢材价格记录。

        返回 ``(记录, 错误信息)``。业务主键 ``(year, month, grade, thickness)``
        重复时返回错误但不抛异常，便于 Router 直接映射为 400 响应。
        """
        payload = data.model_dump()
        try:
            record = self.repository.create(db, payload)
            db.commit()
            db.refresh(record)
            return SteelPriceResponse.model_validate(record), None
        except IntegrityError as error:
            db.rollback()
            message = (
                f"该年度({payload['year']})、月份({payload['month']})、"
                f"牌号({payload['grade']})、厚度({payload['thickness']})的记录已存在"
            )
            logger.warning(
                "创建钢材价格冲突: year=%s month=%s grade=%s thickness=%s, error=%s",
                payload["year"],
                payload["month"],
                payload["grade"],
                payload["thickness"],
                error,
            )
            return None, message
        except Exception as error:
            db.rollback()
            logger.exception("创建钢材价格失败: %s", error)
            return None, str(error)

    def update(
        self, db: Session, record_id: int, data: SteelPriceUpdate
    ) -> tuple[Optional[SteelPriceResponse], Optional[str]]:
        """更新钢材价格记录。

        返回 ``(记录, 错误信息)``；记录不存在时错误以"记录不存在"开头，便于 Router
        映射为 404 状态码。
        """
        payload = data.model_dump(exclude_none=True)
        if not payload:
            return None, "未提供任何可更新字段"

        try:
            record = self.repository.update(db, record_id, payload)
            if record is None:
                db.rollback()
                return None, "记录不存在"
            db.commit()
            db.refresh(record)
            return SteelPriceResponse.model_validate(record), None
        except IntegrityError as error:
            db.rollback()
            logger.warning("更新钢材价格冲突: id=%s, error=%s", record_id, error)
            return None, "更新违反唯一约束"
        except Exception as error:
            db.rollback()
            logger.exception("更新钢材价格失败: id=%s, error=%s", record_id, error)
            return None, str(error)

    def delete(self, db: Session, record_id: int) -> tuple[bool, Optional[str]]:
        """删除钢材价格记录。"""
        try:
            success = self.repository.delete(db, record_id)
            if not success:
                db.rollback()
                return False, "记录不存在"
            db.commit()
            return True, None
        except Exception as error:
            db.rollback()
            logger.exception("删除钢材价格失败: id=%s, error=%s", record_id, error)
            return False, str(error)

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
    ) -> SteelPriceImportResultResponse:
        parse_result = parse_steel_price_excel(file_content)

        try:
            counts = self.repository.upsert(db, parse_result.records)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("导入钢材价格失败: filename=%s", filename)
            raise

        period_labels = sorted(
            {f"{record['year']}-{record['month']:02d}" for record in parse_result.records}
        )
        logger.info(
            "导入钢材价格完成: filename=%s, periods=%s, created=%d, updated=%d",
            filename,
            period_labels,
            counts["created"],
            counts["updated"],
        )
        return SteelPriceImportResultResponse(
            filename=filename,
            imported_count=counts["created"] + counts["updated"],
            created_count=counts["created"],
            updated_count=counts["updated"],
            periods=period_labels,
            warnings=parse_result.warnings,
        )
