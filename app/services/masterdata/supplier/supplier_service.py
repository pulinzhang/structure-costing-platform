"""供应商主数据 Service。"""

from __future__ import annotations

import logging
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.excel_workbook import resolve_worksheet
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.supplier import Supplier
from app.parsers.masterdata.supplier_parser import (
    HEADER_ABBREVIATION,
    HEADER_ALIASES,
    HEADER_ERP_CODE,
    HEADER_FULL_NAME,
    parse_supplier_excel,
)
from app.repositories.masterdata.supplier import SupplierRepository
from app.schemas.dto.supplier_dto import (
    SupplierAliasCreateDTO,
    SupplierAliasInsert,
    SupplierCreateDTO,
    SupplierInsert,
    SupplierPatch,
    SupplierQuery,
    SupplierUpdateDTO,
)
from app.schemas.vo.supplier_vo import (
    SupplierChoiceVO,
    SupplierUploadResultVO,
    SupplierVO,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.supplier")

_PAGE_HINT = "请到供应商一览表手工增加或上传（#/supplier-list）"
_DISABLED_HINT = "请到供应商一览表启用（#/supplier-list）"
_IMPORT_HEADERS = (
    HEADER_ABBREVIATION,
    HEADER_FULL_NAME,
    HEADER_ERP_CODE,
    HEADER_ALIASES,
)


def _catalog_sheet_styles() -> tuple[Font, Font, PatternFill, Alignment, Border]:
    header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    data_font = Font(name="微软雅黑", size=9)
    thin_border = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )
    return header_font, data_font, header_fill, header_alignment, thin_border


def _attach_catalog_sheet(workbook: Workbook) -> tuple[Worksheet, Font, Border]:
    sheet = resolve_worksheet(workbook, "供应商")
    header_font, data_font, header_fill, header_alignment, thin_border = _catalog_sheet_styles()
    for col, title in enumerate(_IMPORT_HEADERS, start=1):
        cell = sheet.cell(row=1, column=col, value=title)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    sheet.column_dimensions["A"].width = 16
    sheet.column_dimensions["B"].width = 40
    sheet.column_dimensions["C"].width = 16
    sheet.column_dimensions["D"].width = 36
    return sheet, data_font, thin_border


def _write_import_row(
    sheet: Worksheet,
    row_idx: int,
    values: tuple[str | None, ...],
    data_font: Font,
    thin_border: Border,
) -> None:
    for col, value in enumerate(values, start=1):
        cell = sheet.cell(row=row_idx, column=col, value=value)
        cell.font = data_font
        cell.border = thin_border


class SupplierService:
    """供应商 CRUD、上传与解析契约。"""

    def __init__(self) -> None:
        self.repository = SupplierRepository()

    def list_enabled(self, db: Session) -> list[SupplierVO]:
        return [self._to_vo(row) for row in self.repository.list_enabled(db)]

    def list_enabled_choices(self, db: Session) -> list[SupplierChoiceVO]:
        return [
            SupplierChoiceVO(full_name=row.full_name, abbreviation=row.abbreviation)
            for row in self.repository.list_enabled(db)
        ]

    def search_enabled_choices(
        self,
        db: Session,
        *,
        keyword: str | None,
        page: int,
        size: int,
    ) -> tuple[list[SupplierChoiceVO], int]:
        skip = (page - 1) * size
        rows, total = self.repository.paginate(
            db,
            keyword=keyword,
            is_enabled=True,
            skip=skip,
            limit=size,
        )
        return [
            SupplierChoiceVO(full_name=row.full_name, abbreviation=row.abbreviation) for row in rows
        ], total

    def list_registered(self, db: Session) -> list[SupplierVO]:
        return [self._to_vo(row) for row in self.repository.list_all(db)]

    def list_registered_names(self, db: Session) -> list[str]:
        return [row.full_name for row in self.repository.list_all(db)]

    def list_page(
        self,
        db: Session,
        query: SupplierQuery,
    ) -> tuple[list[SupplierVO], int]:
        skip = (query.page - 1) * query.size
        rows, total = self.repository.paginate(
            db,
            keyword=query.q,
            is_enabled=query.is_enabled,
            skip=skip,
            limit=query.size,
        )
        return [self._to_vo(row) for row in rows], total

    def resolve_canonical(self, db: Session, raw: str) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None
        by_full = self.repository.get_by_full_name(db, text)
        if by_full is not None:
            return by_full.full_name
        by_abbr = self.repository.get_by_abbreviation(db, text)
        if by_abbr is not None:
            return by_abbr.full_name
        by_erp = self.repository.get_by_erp_code(db, text)
        if by_erp is not None:
            return by_erp.full_name
        alias_row = self.repository.get_alias(db, text)
        if alias_row is not None:
            return alias_row.full_name
        return None

    def require_enabled(self, db: Session, raw: str) -> str:
        canonical = self.resolve_canonical(db, raw)
        if canonical is None:
            raise BusinessException(f"没有该供应商，{_PAGE_HINT}")
        record = self.repository.get_by_full_name(db, canonical)
        if record is None or not record.is_enabled:
            raise BusinessException(f"供应商已禁用，{_DISABLED_HINT}")
        return canonical

    def expand_for_query(self, db: Session, raw: str) -> list[str]:
        canonical = self.resolve_canonical(db, raw)
        if canonical is None:
            return []
        record = self.repository.get_by_full_name(db, canonical)
        if record is None:
            return []
        names = [canonical]
        if record.abbreviation not in names:
            names.append(record.abbreviation)
        if record.erp_code not in names:
            names.append(record.erp_code)
        for alias_row in record.aliases:
            if alias_row.alias not in names:
                names.append(alias_row.alias)
        return names

    def names_for_query(self, db: Session, raw: str | None) -> list[str] | None:
        """None = 不筛；空列表 = 解析失败；非空 = IN 列表。"""
        text = (raw or "").strip()
        if not text:
            return None
        return self.expand_for_query(db, text)

    def is_registered(self, db: Session, full_name: str) -> bool:
        name = (full_name or "").strip()
        if not name:
            return False
        return self.repository.get_by_full_name(db, name) is not None

    def create(
        self,
        db: Session,
        dto: SupplierCreateDTO,
        current_user: UserVO,
    ) -> SupplierVO:
        self._assert_identity_distinct(dto.abbreviation, dto.full_name, dto.erp_code, dto.aliases)
        self._assert_canonical_available(db, dto.full_name)
        self._assert_abbreviation_available(db, dto.abbreviation)
        self._assert_erp_available(db, dto.erp_code)
        for alias in dto.aliases:
            self._assert_alias_available(db, alias)
        audit = audit_create(current_user)
        try:
            record = self.repository.create(
                db,
                SupplierInsert(
                    full_name=dto.full_name,
                    abbreviation=dto.abbreviation,
                    erp_code=dto.erp_code,
                    is_enabled=True,
                    sort_order=self.repository.max_sort_order(db) + 1,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            for alias in dto.aliases:
                self.repository.create_alias(
                    db,
                    SupplierAliasInsert(alias=alias, full_name=record.full_name),
                )
            db.commit()
            db.refresh(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException("该全称已有供应商") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建供应商失败")
            raise
        return self._to_vo(self.repository.get_by_full_name(db, record.full_name) or record)

    def update(
        self,
        db: Session,
        full_name: str,
        dto: SupplierUpdateDTO,
        current_user: UserVO,
    ) -> SupplierVO:
        record = self._require_row(db, full_name)
        data = dto.model_dump(exclude_unset=True)
        if not data:
            raise BusinessException("没有要更新的字段")
        new_abbreviation = data.get("abbreviation", record.abbreviation)
        new_full_name = data.get("full_name", record.full_name)
        new_erp_code = data.get("erp_code", record.erp_code)
        remaining_aliases = [item.alias for item in record.aliases if item.alias != new_full_name]
        self._assert_identity_distinct(
            new_abbreviation,
            new_full_name,
            new_erp_code,
            remaining_aliases,
        )
        old_full_name = record.full_name
        renamed = new_full_name != old_full_name
        if renamed:
            self._assert_canonical_available_for(db, new_full_name, old_full_name)
        if new_abbreviation != record.abbreviation:
            self._assert_abbreviation_available_for(db, new_abbreviation, old_full_name)
        if new_erp_code != record.erp_code:
            self._assert_erp_available_for(db, new_erp_code, old_full_name)
        audit = audit_update(current_user)
        try:
            if renamed:
                alias_row = self.repository.get_alias(db, new_full_name)
                if alias_row is not None and alias_row.full_name == old_full_name:
                    self.repository.delete_alias(db, alias_row)
                self.repository.update_full_name(db, old_full_name, new_full_name)
                record = self._require_row(db, new_full_name)
                occupied = self._lookup_token_owner(db, old_full_name)
                if occupied is not None:
                    raise BusinessException("该名称已被占用")
                self.repository.create_alias(
                    db,
                    SupplierAliasInsert(alias=old_full_name, full_name=new_full_name),
                )
            patch: SupplierPatch = {"updated_by": audit["updated_by"]}
            if new_abbreviation != record.abbreviation:
                patch["abbreviation"] = new_abbreviation
            if new_erp_code != record.erp_code:
                patch["erp_code"] = new_erp_code
            if "is_enabled" in data:
                patch["is_enabled"] = bool(data["is_enabled"])
            self.repository.apply_patch(db, record, patch)
            db.commit()
        except IntegrityError:
            db.rollback()
            if renamed:
                raise BusinessException("仍被引用，不能修改") from None
            raise BusinessException("该全称已有供应商") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新供应商失败")
            raise
        refreshed = self.repository.get_by_full_name(db, new_full_name)
        if refreshed is None:
            raise NotFoundException("供应商不存在")
        return self._to_vo(refreshed)

    def delete(self, db: Session, full_name: str) -> None:
        record = self._require_row(db, full_name)
        try:
            self.repository.delete(db, record)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException("仍被引用，不能删除") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除供应商失败")
            raise

    def add_alias(
        self,
        db: Session,
        full_name: str,
        dto: SupplierAliasCreateDTO,
        current_user: UserVO,
    ) -> SupplierVO:
        record = self._require_row(db, full_name)
        alias = dto.alias
        self._assert_alias_available(db, alias)
        try:
            self.repository.create_alias(
                db,
                SupplierAliasInsert(alias=alias, full_name=record.full_name),
            )
            audit = audit_update(current_user)
            self.repository.apply_patch(
                db,
                record,
                SupplierPatch(updated_by=audit["updated_by"]),
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(f"别名已存在：{alias}", code=409) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("新增别名失败")
            raise
        refreshed = self.repository.get_by_full_name(db, record.full_name)
        if refreshed is None:
            raise NotFoundException("供应商不存在")
        return self._to_vo(refreshed)

    def delete_alias(
        self,
        db: Session,
        full_name: str,
        alias: str,
        current_user: UserVO,
    ) -> SupplierVO:
        record = self._require_row(db, full_name)
        alias_text = (alias or "").strip()
        alias_row = self.repository.get_alias(db, alias_text)
        if alias_row is None or alias_row.full_name != record.full_name:
            raise NotFoundException("别名不存在")
        try:
            self.repository.delete_alias(db, alias_row)
            audit = audit_update(current_user)
            self.repository.apply_patch(
                db,
                record,
                SupplierPatch(updated_by=audit["updated_by"]),
            )
            db.commit()
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除别名失败")
            raise
        refreshed = self.repository.get_by_full_name(db, record.full_name)
        if refreshed is None:
            raise NotFoundException("供应商不存在")
        return self._to_vo(refreshed)

    def process_upload(
        self,
        db: Session,
        file_content: bytes,
        current_user: UserVO,
    ) -> SupplierUploadResultVO:
        parsed = parse_supplier_excel(file_content)
        if parsed.errors:
            raise BusinessException("；".join(parsed.errors))

        errors: list[str] = []
        seen: dict[str, tuple[str, str, frozenset[str]]] = {}
        occupied: dict[str, str] = {}
        pending: list[tuple[SupplierInsert, tuple[str, ...]]] = []
        skipped_count = 0
        audit = audit_create(current_user)

        for row in parsed.rows:
            try:
                self._assert_identity_distinct(
                    row.abbreviation,
                    row.full_name,
                    row.erp_code,
                    list(row.aliases),
                )
            except BusinessException as exc:
                errors.append(f"第 {row.row_number} 行：{exc.message}")
                continue

            signature = (row.abbreviation, row.erp_code, frozenset(row.aliases))
            if row.full_name in seen:
                if seen[row.full_name] == signature:
                    skipped_count += 1
                    continue
                errors.append(
                    f"第 {row.row_number} 行：与文件内已有「{row.full_name}」缩写 / ERP / 别名不一致"
                )
                continue

            tokens = [row.abbreviation, row.full_name, row.erp_code, *row.aliases]
            collision = False
            for token in tokens:
                owner = occupied.get(token)
                if owner is not None and owner != row.full_name:
                    errors.append(f"第 {row.row_number} 行：「{token}」与文件内「{owner}」冲突")
                    collision = True
                    break
            if collision:
                continue

            existing = self.repository.get_by_full_name(db, row.full_name)
            if existing is not None:
                skipped_count += 1
                seen[row.full_name] = signature
                for token in tokens:
                    occupied.setdefault(token, row.full_name)
                continue

            token_error: str | None = None
            try:
                self._assert_abbreviation_available(db, row.abbreviation)
                self._assert_erp_available(db, row.erp_code)
                for alias in row.aliases:
                    self._assert_alias_available(db, alias)
            except BusinessException as exc:
                token_error = exc.message
            if token_error:
                errors.append(f"第 {row.row_number} 行：{token_error}")
                continue

            seen[row.full_name] = signature
            for token in tokens:
                occupied[token] = row.full_name
            pending.append(
                (
                    SupplierInsert(
                        full_name=row.full_name,
                        abbreviation=row.abbreviation,
                        erp_code=row.erp_code,
                        is_enabled=True,
                        sort_order=0,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    ),
                    row.aliases,
                )
            )

        if errors:
            raise BusinessException("；".join(errors))

        try:
            next_sort = self.repository.max_sort_order(db) + 1
            for offset, (payload, aliases) in enumerate(pending):
                payload.sort_order = next_sort + offset
                record = self.repository.create(db, payload)
                for alias in aliases:
                    self.repository.create_alias(
                        db,
                        SupplierAliasInsert(alias=alias, full_name=record.full_name),
                    )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException("该全称已有供应商") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("导入供应商失败")
            raise
        return SupplierUploadResultVO(
            created_count=len(pending),
            skipped_count=skipped_count,
        )

    def write_catalog_to_workbook(
        self,
        db: Session,
        workbook: Workbook,
        *,
        keyword: str | None = None,
        is_enabled: bool | None = True,
    ) -> None:
        records = self.repository.list_for_export(
            db,
            keyword=keyword,
            is_enabled=is_enabled,
        )
        sheet, data_font, thin_border = _attach_catalog_sheet(workbook)
        for row_idx, record in enumerate(records, start=2):
            aliases = "、".join(item.alias for item in record.aliases)
            _write_import_row(
                sheet,
                row_idx,
                (record.abbreviation, record.full_name, record.erp_code, aliases or None),
                data_font,
                thin_border,
            )

    def build_template(self) -> tuple[bytes, str]:
        workbook = Workbook()
        sheet, data_font, thin_border = _attach_catalog_sheet(workbook)
        _write_import_row(
            sheet,
            2,
            ("常庆", "安庆常庆汽车部件有限公司", "CQ001", "常庆汽配、安庆常庆"),
            data_font,
            thin_border,
        )
        buffer = BytesIO()
        workbook.save(buffer)
        workbook.close()
        return buffer.getvalue(), "供应商导入模板.xlsx"

    def export_excel(
        self,
        db: Session,
        current_user: UserVO,
        *,
        keyword: str | None = None,
        is_enabled: bool | None = None,
    ) -> tuple[bytes, str]:
        workbook = Workbook()
        self.write_catalog_to_workbook(
            db,
            workbook,
            keyword=keyword,
            is_enabled=is_enabled,
        )
        stamp = now().strftime("%Y%m%d_%H%M%S")
        return workbook_to_xlsx_bytes(workbook, current_user), f"供应商一览_{stamp}.xlsx"

    def _require_row(self, db: Session, full_name: str) -> Supplier:
        name = (full_name or "").strip()
        record = self.repository.get_by_full_name(db, name)
        if record is None:
            raise NotFoundException("供应商不存在")
        return record

    def _assert_identity_distinct(
        self,
        abbreviation: str,
        full_name: str,
        erp_code: str,
        aliases: list[str],
    ) -> None:
        tokens = [abbreviation, full_name, erp_code, *aliases]
        seen: set[str] = set()
        for token in tokens:
            if token in seen:
                raise BusinessException("缩写、全称、ERP 代码与别名不得相同")
            seen.add(token)

    def _lookup_token_owner(self, db: Session, token: str) -> str | None:
        by_full = self.repository.get_by_full_name(db, token)
        if by_full is not None:
            return by_full.full_name
        by_abbr = self.repository.get_by_abbreviation(db, token)
        if by_abbr is not None:
            return by_abbr.full_name
        by_erp = self.repository.get_by_erp_code(db, token)
        if by_erp is not None:
            return by_erp.full_name
        alias_row = self.repository.get_alias(db, token)
        if alias_row is not None:
            return alias_row.full_name
        return None

    def _assert_canonical_available(self, db: Session, name: str) -> None:
        owner = self._lookup_token_owner(db, name)
        if owner is not None:
            raise BusinessException("该全称已有供应商")

    def _assert_canonical_available_for(self, db: Session, name: str, owner: str) -> None:
        current = self._lookup_token_owner(db, name)
        if current is not None and current != owner:
            raise BusinessException("该全称已有供应商")

    def _assert_abbreviation_available(self, db: Session, name: str) -> None:
        if self._lookup_token_owner(db, name) is not None:
            raise BusinessException("该缩写已被占用")

    def _assert_abbreviation_available_for(self, db: Session, name: str, owner: str) -> None:
        current = self._lookup_token_owner(db, name)
        if current is not None and current != owner:
            raise BusinessException("该缩写已被占用")

    def _assert_erp_available(self, db: Session, name: str) -> None:
        if self._lookup_token_owner(db, name) is not None:
            raise BusinessException("该 ERP 代码已被占用")

    def _assert_erp_available_for(self, db: Session, name: str, owner: str) -> None:
        current = self._lookup_token_owner(db, name)
        if current is not None and current != owner:
            raise BusinessException("该 ERP 代码已被占用")

    def _assert_alias_available(self, db: Session, name: str) -> None:
        if self._lookup_token_owner(db, name) is not None:
            raise BusinessException("别名不得等于已有缩写、全称、ERP 代码或别名")

    def _to_vo(self, row: Supplier) -> SupplierVO:
        return SupplierVO(
            full_name=row.full_name,
            abbreviation=row.abbreviation,
            erp_code=row.erp_code,
            is_enabled=row.is_enabled,
            sort_order=row.sort_order,
            aliases=[item.alias for item in row.aliases],
            created_by=row.created_by,
            updated_by=row.updated_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
