"""供应商主数据 Service（门面，符号路径保持不变）。"""

from __future__ import annotations

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.repositories.masterdata.supplier import SupplierRepository
from app.schemas.dto.supplier_dto import (
    SupplierAliasCreateDTO,
    SupplierCreateDTO,
    SupplierQuery,
    SupplierUpdateDTO,
)
from app.schemas.vo.supplier_vo import (
    SupplierChoiceVO,
    SupplierUploadResultVO,
    SupplierVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.supplier.catalog import (
    build_template as build_catalog_template,
)
from app.services.masterdata.supplier.catalog import (
    export_excel as export_catalog_excel,
)
from app.services.masterdata.supplier.catalog import write_catalog_to_workbook
from app.services.masterdata.supplier.crud import (
    add_alias as add_supplier_alias,
)
from app.services.masterdata.supplier.crud import (
    create_supplier,
    delete_supplier,
    list_enabled,
    list_enabled_choices,
    list_page,
    list_registered,
    list_registered_names,
    search_enabled_choices,
    update_supplier,
)
from app.services.masterdata.supplier.crud import (
    delete_alias as delete_supplier_alias,
)
from app.services.masterdata.supplier.identity import (
    expand_for_query,
    is_registered,
    names_for_query,
    require_enabled,
    resolve_canonical,
)
from app.services.masterdata.supplier.upload import process_upload as process_supplier_upload


class SupplierService:
    """供应商 CRUD、上传与解析契约。"""

    def __init__(self) -> None:
        self.repository = SupplierRepository()

    def list_enabled(self, db: Session) -> list[SupplierVO]:
        return list_enabled(self.repository, db)

    def list_enabled_choices(self, db: Session) -> list[SupplierChoiceVO]:
        return list_enabled_choices(self.repository, db)

    def search_enabled_choices(
        self,
        db: Session,
        *,
        keyword: str | None,
        page: int,
        size: int,
    ) -> tuple[list[SupplierChoiceVO], int]:
        return search_enabled_choices(self.repository, db, keyword=keyword, page=page, size=size)

    def list_registered(self, db: Session) -> list[SupplierVO]:
        return list_registered(self.repository, db)

    def list_registered_names(self, db: Session) -> list[str]:
        return list_registered_names(self.repository, db)

    def list_page(
        self,
        db: Session,
        query: SupplierQuery,
    ) -> tuple[list[SupplierVO], int]:
        return list_page(self.repository, db, query)

    def resolve_canonical(self, db: Session, raw: str) -> str | None:
        return resolve_canonical(self.repository, db, raw)

    def require_enabled(self, db: Session, raw: str) -> str:
        return require_enabled(self.repository, db, raw)

    def expand_for_query(self, db: Session, raw: str) -> list[str]:
        return expand_for_query(self.repository, db, raw)

    def names_for_query(self, db: Session, raw: str | None) -> list[str] | None:
        return names_for_query(self.repository, db, raw)

    def is_registered(self, db: Session, full_name: str) -> bool:
        return is_registered(self.repository, db, full_name)

    def create(
        self,
        db: Session,
        dto: SupplierCreateDTO,
        current_user: UserVO,
    ) -> SupplierVO:
        return create_supplier(self.repository, db, dto, current_user)

    def update(
        self,
        db: Session,
        full_name: str,
        dto: SupplierUpdateDTO,
        current_user: UserVO,
    ) -> SupplierVO:
        return update_supplier(self.repository, db, full_name, dto, current_user)

    def delete(self, db: Session, full_name: str) -> None:
        delete_supplier(self.repository, db, full_name)

    def add_alias(
        self,
        db: Session,
        full_name: str,
        dto: SupplierAliasCreateDTO,
        current_user: UserVO,
    ) -> SupplierVO:
        return add_supplier_alias(self.repository, db, full_name, dto, current_user)

    def delete_alias(
        self,
        db: Session,
        full_name: str,
        alias: str,
        current_user: UserVO,
    ) -> SupplierVO:
        return delete_supplier_alias(self.repository, db, full_name, alias, current_user)

    def process_upload(
        self,
        db: Session,
        file_content: bytes,
        current_user: UserVO,
    ) -> SupplierUploadResultVO:
        return process_supplier_upload(self.repository, db, file_content, current_user)

    def write_catalog_to_workbook(
        self,
        db: Session,
        workbook: Workbook,
        *,
        keyword: str | None = None,
        is_enabled: bool | None = True,
    ) -> None:
        write_catalog_to_workbook(
            self.repository,
            db,
            workbook,
            keyword=keyword,
            is_enabled=is_enabled,
        )

    def build_template(self) -> tuple[bytes, str]:
        return build_catalog_template()

    def export_excel(
        self,
        db: Session,
        current_user: UserVO,
        *,
        keyword: str | None = None,
        is_enabled: bool | None = None,
    ) -> tuple[bytes, str]:
        return export_catalog_excel(
            self.repository,
            db,
            current_user,
            keyword=keyword,
            is_enabled=is_enabled,
        )
