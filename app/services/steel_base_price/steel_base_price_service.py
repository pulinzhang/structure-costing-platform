"""钢材基准价格业务服务。"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.parsers.steel_base_price import parse_base_price_excel
from app.repositories.steel_base_price import SteelBasePriceRepository
from app.schemas.dto.steel_base_price_dto import FilterOptions
from app.schemas.vo.steel_base_price_vo import (
    FilterOptionsVO,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)

logger = logging.getLogger("service.steel_base_price")


class SteelBasePriceService:
    """钢材基准价格查询与导入业务。"""

    def __init__(self) -> None:
        self.repository = SteelBasePriceRepository()

    def get_filter_options(self, db: Session) -> FilterOptions:
        """获取筛选下拉选项（供 Router 转换为 VO）。"""
        return self.repository.get_filter_options(db)

    def paginate(
        self,
        db: Session,
        query: SteelBasePriceQuery,
    ) -> tuple[list[SteelBasePriceResponse], int]:
        """分页浏览基准价格。"""
        from app.repositories.steel_base_price.steel_base_price_repository import (
            BasePriceFilter,
        )

        skip = (query.page - 1) * query.size
        base_filter = BasePriceFilter(
            year=query.year,
            month=query.month,
            location=query.location.strip() if query.location else None,
            steel_mill=query.steel_mill.strip() if query.steel_mill else None,
            category_name=query.category_name.strip() if query.category_name else None,
            grade=query.grade.strip() if query.grade else None,
            spec=query.spec.strip() if query.spec else None,
            skip=skip,
            limit=query.size,
        )
        records, total = self.repository.paginate(db, base_filter)
        return [SteelBasePriceResponse.model_validate(r) for r in records], total

    def get_by_id(self, db: Session, record_id: int) -> SteelBasePriceResponse | None:
        """获取单条记录。"""
        record = self.repository.get_by_id(db, record_id)
        if record is None:
            return None
        return SteelBasePriceResponse.model_validate(record)

    def create(self, db: Session, body: SteelBasePriceCreate) -> tuple[SteelBasePriceResponse | None, str | None]:
        """创建基准价格记录。"""
        try:
            data = body.model_dump()
            record = self.repository.create(db, data)
            db.commit()
            return SteelBasePriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.exception("创建基准价格失败")
            return None, str(e)

    def update(self, db: Session, record_id: int, body: SteelBasePriceUpdate) -> tuple[SteelBasePriceResponse | None, str | None]:
        """更新基准价格记录。"""
        try:
            data = body.model_dump(exclude_unset=True)
            if not data:
                return None, "没有提供任何更新字段"
            record = self.repository.update(db, record_id, data)
            if record is None:
                return None, "记录不存在"
            db.commit()
            return SteelBasePriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.exception("更新基准价格失败: id=%s", record_id)
            return None, str(e)

    def delete(self, db: Session, record_id: int) -> tuple[bool, str | None]:
        """删除基准价格记录。"""
        try:
            success = self.repository.delete(db, record_id)
            if not success:
                return False, "记录不存在"
            db.commit()
            return True, None
        except Exception as e:
            db.rollback()
            logger.exception("删除基准价格失败: id=%s", record_id)
            return False, str(e)

    def batch_delete(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None = None,
        steel_mill: str | None = None,
    ) -> tuple[bool, str | None]:
        """按条件批量删除（年度+月份必须同时指定）。"""
        try:
            count = self.repository.delete_by_conditions(
                db,
                year=year,
                month=month,
                location=location,
                steel_mill=steel_mill,
            )
            db.commit()
            logger.info("批量删除基准价格: year=%s month=%s location=%s steel_mill=%s count=%s",
                year, month, location, steel_mill, count)
            return True, None
        except Exception as e:
            db.rollback()
            logger.exception("批量删除基准价格失败")
            return False, str(e)

    def import_excel(
        self,
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        year: int,
        month: int,
    ) -> SteelBasePriceImportResultResponse:
        """
        解析 Excel 并执行 upsert。

        Args:
            db: 数据库会话
            file_content: Excel 文件字节内容
            filename: 文件名（注入到 excel_filename 字段）
            year: 生效年度
            month: 生效月份

        Returns:
            导入结果（created/updated/total/warnings）
        """
        parse_result = parse_base_price_excel(file_content)

        # 注入文件名、年度、月份，修正 grade 中的 //
        for record in parse_result.records:
            record["excel_filename"] = filename
            record["year"] = year
            record["month"] = month
        if not parse_result.records:
            return SteelBasePriceImportResultResponse(
                filename=filename,
                created_count=0,
                updated_count=0,
                total=0,
                warnings=parse_result.warnings,
                errors=parse_result.errors,
            )

        try:
            counts = self.repository.upsert(db, parse_result.records)
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

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        spec: str | None = None,
    ) -> list[SteelBasePriceResponse]:
        """导出预览数据（分批）。"""
        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            spec=spec,
        )
        return [SteelBasePriceResponse.model_validate(r) for r in records]