"""
冲压工艺 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.money import Q2, Q4, optional_format_money
from app.exceptions import BusinessException, NotFoundException
from app.models.stamping import StampingPart
from app.repositories.stamping.stamping_part_repository import MaterialSpecRow
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_part_dto import (
    StampingPartBatchDeleteDTO,
    StampingPartOffalUpdateDTO,
)
from app.schemas.dto.stamping_upload_dto import (
    PartData,
    StampingPartPatch,
    StampingProcessPatch,
)
from app.schemas.vo.stamping_vo import (
    StampingCascadeFilterOptionsVO,
    StampingCascadeFilterQuery,
    StampingMaterialQuery,
    StampingMaterialResponse,
    StampingPartBatchDeleteResultVO,
    StampingPartListFilterOptions,
    StampingPartListResponse,
    StampingPartListSummaryVO,
    StampingPartQuery,
    StampingPartResponse,
    StampingPartWithProcessesResponse,
    StampingProcessItemUpdate,
    StampingProcessResponse,
    StampingProcessUpdate,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.stamping")


def _join_formatted_numbers(
    values: list[Decimal | None],
    quant: Decimal,
    places: int,
) -> str | None:
    """按顺序把数值格式化后用 / 拼接；全空则 None。"""
    texts: list[str] = []
    for value in values:
        text = optional_format_money(value, quant, places)
        if text is not None:
            texts.append(text)
    if not texts:
        return None
    return "/".join(texts)


def _material_row_from_part(part: StampingPart) -> StampingMaterialResponse:
    """普通件用主表尺寸；拼焊件用各子片料厚/长/宽拼接。"""
    blanks = sorted(
        list(part.tailor_weld_blanks or []),
        key=lambda blank: (blank.blank_seq or 0, blank.id or 0),
    )
    material = (part.material or "").strip() or None
    if part.is_tailor_welded and len(blanks) >= 2:
        if not material:
            material = (blanks[0].material or "").strip() or None
        return StampingMaterialResponse(
            material=material,
            thickness=_join_formatted_numbers([blank.thickness for blank in blanks], Q2, 2),
            sheet_length=_join_formatted_numbers([blank.sheet_length for blank in blanks], Q2, 2),
            sheet_width=_join_formatted_numbers([blank.sheet_width for blank in blanks], Q2, 2),
        )
    return StampingMaterialResponse(
        material=material,
        thickness=optional_format_money(part.thickness, Q4, 4),
        sheet_length=optional_format_money(part.sheet_length, Q2, 2),
        sheet_width=optional_format_money(part.sheet_width, Q2, 2),
    )


class StampingPartService:
    """零件业务逻辑"""

    def __init__(self) -> None:
        self.repository = StampingPartRepository()
        self.process_repository = StampingProcessRepository()

    def count_parts(self, db: Session) -> int:
        """零件总数。"""
        return self.repository.count_all(db)

    def count_processes(self, db: Session) -> int:
        """工序总数。"""
        return self.process_repository.count_all(db)

    def count_vehicle_models(self, db: Session) -> int:
        """去重车型数量。"""
        return self.repository.count_distinct_vehicle_models(db)

    def summarize_master(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> dict[str, int]:
        """按基地 / 车型汇总主数据：零件数 / 工序数 / 车型数。"""
        location_clean = location.strip() if location else None
        vehicle_clean = vehicle_model.strip() if vehicle_model else None
        _rows, parts = self.repository.paginate(
            db,
            location=location_clean,
            vehicle_model=vehicle_clean,
            skip=0,
            limit=1,
        )
        summary = self.repository.summarize_by_filters(
            db,
            location=location_clean,
            vehicle_model=vehicle_clean,
        )
        return {
            "parts": int(parts),
            "processes": self.process_repository.count_by_part_location(
                db,
                location_clean,
                vehicle_clean,
            ),
            "models": int(summary.get("vehicle_model_count") or 0),
        }

    def list_parts(
        self, db: Session, query: StampingPartQuery
    ) -> tuple[list[StampingPartListResponse], int, StampingPartListFilterOptions]:
        """获取零件列表（不含工序详情，含工序统计数 process_count）"""
        skip = (query.page - 1) * query.size
        location = query.location
        vehicle_model = query.vehicle_model
        version = query.version
        part_number = query.part_number
        part_name = query.part_name
        stamping_supplier = query.stamping_supplier
        parts, total = self.repository.paginate(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
            skip=skip,
            limit=query.size,
        )
        # 一次聚合查询补齐每行工序数（避免 ORM lazy load 触发 N+1）
        part_ids = [p.id for p in parts]
        process_counts = self.repository.count_processes_by_part_ids(db, part_ids)

        rows = []
        for p in parts:
            row = StampingPartListResponse.model_validate(p)
            row.process_count = process_counts.get(p.id, 0)
            rows.append(row)

        # 筛选下拉框选项 + 当前筛选下去重维度汇总
        raw = self.repository.get_filter_options(db)
        filter_vo = StampingPartListFilterOptions(
            locations=list(raw["locations"]),
            vehicle_models=list(raw["vehicle_models"]),
            versions=list(raw["versions"]),
            materials=list(raw["materials"]),
            stamping_suppliers=list(raw["stamping_suppliers"]),
            summary=StampingPartListSummaryVO.model_validate(
                self.repository.summarize_by_filters(
                    db,
                    location=location,
                    vehicle_model=vehicle_model,
                    version=version,
                    part_number=part_number,
                    part_name=part_name,
                    stamping_supplier=stamping_supplier,
                )
            ),
        )
        return rows, total, filter_vo

    def get_filter_options(self, db: Session) -> StampingPartListFilterOptions:
        """获取筛选下拉框的可选值"""
        raw = self.repository.get_filter_options(db)
        return StampingPartListFilterOptions.model_validate(raw)

    def get_cascade_filter_options(
        self,
        db: Session,
        query: StampingCascadeFilterQuery,
    ) -> StampingCascadeFilterOptionsVO:
        """获取基地 → 车型 → 版本 → 冲压工厂 级联筛选选项"""
        raw = self.repository.get_cascade_filter_options(
            db,
            location=query.location.strip() if query.location else None,
            stamping_supplier=query.stamping_supplier.strip() if query.stamping_supplier else None,
            vehicle_model=query.vehicle_model.strip() if query.vehicle_model else None,
            version=query.version.strip() if query.version else None,
        )
        return StampingCascadeFilterOptionsVO.model_validate(raw)

    def list_materials(
        self, db: Session, query: StampingMaterialQuery
    ) -> tuple[list[StampingMaterialResponse], int, StampingPartListFilterOptions]:
        """获取材料列表（去重；拼焊件厚度/长/宽为子片拼接）。"""
        skip = (query.page - 1) * query.size
        parts = self.repository.list_parts_for_materials(
            db,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
        )

        unique_rows: list[StampingMaterialResponse] = []
        seen: set[tuple[str | None, str | None, str | None, str | None]] = set()
        for part in parts:
            row = _material_row_from_part(part)
            key = (row.material, row.thickness, row.sheet_length, row.sheet_width)
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(row)

        unique_rows.sort(
            key=lambda row: (
                row.material or "",
                row.thickness or "",
                row.sheet_length or "",
                row.sheet_width or "",
            )
        )
        total = len(unique_rows)
        page_rows = unique_rows[skip : skip + query.size]
        filter_options = self.repository.get_filter_options(db)
        filter_vo = StampingPartListFilterOptions.model_validate(filter_options)
        return page_rows, total, filter_vo

    def count_material_specs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> int:
        """统计去重后的材料+厚度规格行数（含拼焊子片；统计可按车型收窄）。"""
        loc = location.strip() if location else None
        vehicle = vehicle_model.strip() if vehicle_model else None
        if not loc and not vehicle:
            return 0
        return self.repository.count_material_specs(
            db,
            location=loc,
            vehicle_model=vehicle,
        )

    def list_distinct_spec_grades(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        """统计用：范围内去重牌号（含拼焊子片）。"""
        loc = location.strip() if location else None
        vehicle = vehicle_model.strip() if vehicle_model else None
        if not loc and not vehicle:
            return []
        return self.repository.list_distinct_spec_grades(
            db,
            location=loc,
            vehicle_model=vehicle,
        )

    def list_material_specs(self, db: Session, *, location: str) -> list[MaterialSpecRow]:
        """列出该基地去重后的 基地 + 材料(钢种) + 厚度（含拼焊子片，钢价计算用）。"""
        loc = location.strip()
        if not loc:
            return []
        return self.repository.list_material_specs(db, location=loc)

    def get_by_id(self, db: Session, part_id: int) -> StampingPartWithProcessesResponse:
        """获取单个零件（含工序）"""
        part = self.repository.get_by_id(db, part_id)
        if not part:
            raise NotFoundException(f"零件不存在: id={part_id}")
        return StampingPartWithProcessesResponse.model_validate(part)

    def delete(self, db: Session, part_id: int) -> None:
        """删除零件（硬删除，不写审计字段）。"""
        deleted = self.repository.delete(db, part_id)
        if not deleted:
            raise NotFoundException(f"零件不存在: id={part_id}")
        db.commit()

    def create(
        self,
        db: Session,
        part_data: PartData,
        current_user: UserVO,
    ) -> StampingPart:
        audit = audit_create(current_user)
        part_data.created_by = audit["created_by"]
        part_data.updated_by = audit["updated_by"]
        part = self.repository.create(db, part_data)
        db.commit()
        db.refresh(part)
        return part

    def bulk_create(
        self,
        db: Session,
        parts_data: list[PartData],
        current_user: UserVO,
    ) -> list[StampingPart]:
        audit = audit_create(current_user)
        for row in parts_data:
            row.created_by = audit["created_by"]
            row.updated_by = audit["updated_by"]
        parts = self.repository.bulk_create(db, parts_data)
        db.commit()
        return parts

    def update(
        self,
        db: Session,
        part_id: int,
        update_data: StampingPartPatch,
        current_user: UserVO,
    ) -> StampingPart | None:
        payload: StampingPartPatch = {**update_data}
        payload["updated_by"] = display_name(current_user)
        part = self.repository.update(db, part_id, payload)
        if part is not None:
            db.commit()
            db.refresh(part)
        return part

    def update_offal(
        self,
        db: Session,
        part_id: int,
        dto: StampingPartOffalUpdateDTO,
        current_user: UserVO,
    ) -> StampingPartResponse:
        """零件详情纠错：是否利废、利用哪类废料。关开关时清空废料来源。"""
        source = None if not dto.is_offal_nested else dto.offal_source
        payload: StampingPartPatch = {
            "is_offal_nested": dto.is_offal_nested,
            "offal_source": source,
            "updated_by": display_name(current_user),
        }
        part = self.repository.update(db, part_id, payload)
        if not part:
            raise NotFoundException(f"零件不存在: id={part_id}")
        db.commit()
        db.refresh(part)
        return StampingPartResponse.model_validate(part)

    def batch_delete(
        self,
        db: Session,
        dto: StampingPartBatchDeleteDTO,
    ) -> StampingPartBatchDeleteResultVO:
        """按基地 + 车型 + 版本批量删除零件；工厂可选。"""
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        version = dto.version.strip()
        supplier = dto.stamping_supplier
        if not location or not vehicle_model or not version:
            raise BusinessException("基地、车型和版本不能为空")

        deleted = self.repository.delete_by_scope(
            db,
            location=location,
            stamping_supplier=supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        db.commit()
        return StampingPartBatchDeleteResultVO(
            location=location,
            stamping_supplier=supplier,
            vehicle_model=vehicle_model,
            version=version,
            deleted_count=deleted,
        )

    def update_process(
        self,
        db: Session,
        process_id: int,
        dto: StampingProcessUpdate,
        current_user: UserVO,
    ) -> StampingProcessResponse:
        """更新单个工序"""
        process_repo = StampingProcessRepository()
        payload: StampingProcessPatch = {
            "updated_by": display_name(current_user),
        }
        if "cost_ratio" in dto.model_fields_set and dto.cost_ratio is not None:
            payload["cost_ratio"] = dto.cost_ratio
        if "remark" in dto.model_fields_set:
            payload["remark"] = dto.remark
        if len(payload) == 1:
            logger.warning("process_id=%s 的更新字段为空", process_id)
        process = process_repo.update(db, process_id, payload)
        if not process:
            raise NotFoundException(f"工序不存在: id={process_id}")
        db.commit()
        db.refresh(process)
        return StampingProcessResponse.model_validate(process)

    def batch_update_processes(
        self,
        db: Session,
        items: list[StampingProcessItemUpdate],
        current_user: UserVO,
    ) -> int:
        """批量更新工序成本系数"""
        operator_name = display_name(current_user)
        process_repo = StampingProcessRepository()
        count = 0
        for item in items:
            payload: StampingProcessPatch = {
                "updated_by": operator_name,
            }
            if "cost_ratio" in item.model_fields_set and item.cost_ratio is not None:
                payload["cost_ratio"] = item.cost_ratio
            if "remark" in item.model_fields_set:
                payload["remark"] = item.remark
            if len(payload) == 1:
                logger.warning("process_id=%s 的 update_data 为空，跳过", item.id)
                continue
            if process_repo.update(db, item.id, payload):
                count += 1
        db.commit()
        logger.info("batch_update_processes 完成，更新了 %s 条", count)
        return count
