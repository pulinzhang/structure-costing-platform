"""钢材基准价格业务服务。"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.parsers.steel_base_price import parse_base_price_excel
from app.repositories.steel_base_price import SteelBasePriceRepository
from app.schemas.dto.steel_base_price_dto import FilterOptions
from app.schemas.vo.steel_base_price_vo import (
    FilterOptionsVO,
    SteelBasePriceExportRow,
    SteelBasePriceImportResultResponse,
    SteelBasePriceResponse,
)
from app.schemas.dto.steel_base_price_dto import (
    SteelBasePriceCreate,
    SteelBasePriceQuery,
    SteelBasePriceUpdate,
)
from app.schemas.vo.user_vo import UserVO
from app.utils.steel_price_archive import (
    FILE_KIND_BASE_PRICE,
    save_steel_price_upload,
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

    def create(
        self,
        db: Session,
        body: SteelBasePriceCreate,
        current_user: UserVO,
    ) -> tuple[SteelBasePriceResponse | None, str | None]:
        """创建基准价格记录。"""
        try:
            data = {**body.model_dump(), **audit_create(current_user)}
            record = self.repository.create(db, data)
            db.commit()
            return SteelBasePriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.exception("创建基准价格失败")
            return None, str(e)

    def update(
        self,
        db: Session,
        record_id: int,
        body: SteelBasePriceUpdate,
        current_user: UserVO,
    ) -> tuple[SteelBasePriceResponse | None, str | None]:
        """更新基准价格记录。"""
        try:
            data = body.model_dump(exclude_unset=True)
            if not data:
                return None, "没有提供任何更新字段"
            data.update(audit_update(current_user))
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
        current_user: UserVO,
        progress_callback=None,
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

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        spec: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[SteelBasePriceExportRow], int]:
        """导出预览数据（支持前端分页）。返回 (items, total)。"""
        skip = None
        limit = None
        if page is not None and page_size is not None:
            skip = (page - 1) * page_size
            limit = page_size

        category = category_name.strip() if category_name else None
        grade_value = grade.strip() if grade else None

        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category,
            grade=grade_value,
            spec=spec,
            skip=skip,
            limit=limit,
        )
        total = self.repository.count_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category,
            grade=grade_value,
            spec=spec,
        )
        return [SteelBasePriceExportRow.model_validate(r) for r in records], total

    def list_for_calc(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ):
        """钢价计算用：按年/月/基地取出全部基价 ORM（含 id 溯源）。"""
        from app.models.steel_base_price import SteelBasePrice

        records: list[SteelBasePrice] = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location.strip() if location else None,
        )
        return records

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        steel_mill: str | None = None,
        spec: str | None = None,
    ) -> int:
        """按条件统计基准价格条数。"""
        return self.repository.count_for_export(
            db,
            year=year,
            month=month,
            location=location.strip() if location else None,
            steel_mill=steel_mill.strip() if steel_mill else None,
            spec=spec.strip() if spec else None,
        )
