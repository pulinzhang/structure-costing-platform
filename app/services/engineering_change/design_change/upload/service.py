"""工程变更上传 Service 门面（模板 + 入队入口转发）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.design_change.upload.start_upload import (
    start_upload as start_upload_fn,
)
from app.services.engineering_change.design_change.upload.template_builder import (
    TemplateMeta,
    build_engineering_change_template,
    example_book,
)
from app.services.masterdata.vehicle_model.service import VehicleModelService

_PLACEHOLDER_CUSTOMER = "请填写顾客名称"
_PLACEHOLDER_SUPPLIER = "请填写冲压工厂"
_PLACEHOLDER_BOM_VERSION = "已上传的材料清单版本"
_snapshot_repo = BomSnapshotRepository()


class EngineeringChangeUploadService:
    """Router 只依赖本类。"""

    @staticmethod
    def build_template(
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        effective_year: int,
        effective_month: int,
    ) -> tuple[bytes, str]:
        location, vehicle_model = VehicleModelService().require_introducible(
            db,
            location.strip(),
            vehicle_model.strip(),
            effective_year,
            effective_month,
        )
        customer_name, bom_version = _example_header(db, location, vehicle_model)
        period = f"{effective_year}年{effective_month:02d}月"
        meta = TemplateMeta(
            location=location,
            vehicle_model=vehicle_model,
            customer_name=customer_name,
            period_label=period,
            change_version=f"EC-{effective_year}{effective_month:02d}",
            stamping_supplier=_PLACEHOLDER_SUPPLIER,
            bom_version_label=bom_version,
            header_date=f"{effective_year}-{effective_month:02d}-01",
            doc_no=f"EC-{vehicle_model}-{effective_year}{effective_month:02d}",
        )
        return build_engineering_change_template(example_book(meta))

    @staticmethod
    def start_upload(
        db: Session,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        effective_year: int,
        effective_month: int,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        return start_upload_fn(
            db,
            file_content=file_content,
            filename=filename,
            location=location,
            vehicle_model=vehicle_model,
            effective_year=effective_year,
            effective_month=effective_month,
            current_user=current_user,
        )


def _example_header(db: Session, location: str, vehicle_model: str) -> tuple[str, str]:
    """举例抬头用该项目已有材料清单的顾客和版本；没有清单就留空位让人自己填。"""
    rows = _snapshot_repo.list_by_location_model(db, location, vehicle_model)
    production = [row for row in rows if not (row.bom_version or "").upper().startswith("EC")]
    chosen = production[0] if production else (rows[0] if rows else None)
    if chosen is None:
        return _PLACEHOLDER_CUSTOMER, _PLACEHOLDER_BOM_VERSION
    customer_name = (chosen.customer_name or "").strip() or _PLACEHOLDER_CUSTOMER
    bom_version = (chosen.bom_version or "").strip() or _PLACEHOLDER_BOM_VERSION
    return customer_name, bom_version
