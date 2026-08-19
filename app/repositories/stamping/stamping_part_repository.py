"""冲压零件数据访问。"""

import logging
from collections.abc import Sequence
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, TypeVar, TypedDict

from sqlalchemy import func
from sqlalchemy.orm import InstrumentedAttribute, Query, Session
from sqlalchemy.sql.selectable import Subquery

from app.models import StampingPart, StampingProcess
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_upload_dto import PartData, StampingPartPatch

_T = TypeVar("_T")
_StringColumn = InstrumentedAttribute[str] | InstrumentedAttribute[str | None]


class StampingPartFilterOptionValues(TypedDict):
    """筛选下拉选项（不含列表汇总，汇总由 Service 拼入）。"""

    locations: list[str]
    stamping_suppliers: list[str]
    vehicle_models: list[str]
    versions: list[str]
    materials: list[str]


class MaterialSpecRow(TypedDict):
    """去重后的材料规格行（钢价 Step1）。"""

    location: str
    material: str
    thickness: Decimal


logger = logging.getLogger("repository.stamping.part")


class StampingPartRepository:
    """零件数据访问"""

    def count_all(self, db: Session) -> int:
        """零件总数。"""
        return db.query(StampingPart).count()

    def count_distinct_vehicle_models(self, db: Session) -> int:
        """去重车型数量。"""
        return db.query(StampingPart.vehicle_model).distinct().count()

    def get_by_id(self, db: Session, part_id: int) -> Optional[StampingPart]:
        from sqlalchemy.orm import selectinload
        return (
            db.query(StampingPart)
            .options(selectinload(StampingPart.processes))
            .filter(StampingPart.id == part_id)
            .first()
        )

    def get_by_part_number(self, db: Session, part_number: str) -> Optional[StampingPart]:
        return db.query(StampingPart).filter(StampingPart.part_number == part_number).first()

    def filter_by_vehicle_version(
        self,
        db: Session,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
    ) -> Tuple[List[StampingPart], int]:
        """查询零件，返回 (结果列表, 总数)"""
        q = db.query(StampingPart)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))
        if stamping_supplier is not None:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)

        total = q.count()
        from sqlalchemy.orm import selectinload
        parts = (
            q.options(selectinload(StampingPart.processes))
            .order_by(StampingPart.seq_no)
            .all()
        )
        return parts, total

    def _build_list_query(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
    ) -> Query[StampingPart]:
        """构建与列表相同的筛选查询（不含排序/分页）。"""
        q = db.query(StampingPart)
        if location is not None:
            q = q.filter(StampingPart.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)
        if part_number:
            q = q.filter(StampingPart.part_number.like(f"%{part_number}%"))
        if part_name:
            q = q.filter(StampingPart.part_name.like(f"%{part_name}%"))
        return q

    def paginate(
        self,
        db: Session,
        location: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StampingPart], int]:
        """分页查询零件"""
        q = self._build_list_query(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
        )
        total = q.count()
        parts = q.order_by(StampingPart.id).offset(skip).limit(limit).all()
        return parts, total

    def summarize_by_filters(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
    ) -> Dict[str, int]:
        """按与列表相同的筛选条件汇总去重维度数量。"""
        q = self._build_list_query(
            db,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
            stamping_supplier=stamping_supplier,
        )
        row = q.with_entities(
            func.count(func.distinct(StampingPart.location)).label("location_count"),
            func.count(func.distinct(StampingPart.stamping_supplier)).label(
                "stamping_supplier_count"
            ),
            func.count(func.distinct(StampingPart.vehicle_model)).label(
                "vehicle_model_count"
            ),
            func.count(func.distinct(StampingPart.part_number)).label(
                "part_number_count"
            ),
            func.count(func.distinct(StampingPart.version)).label("version_count"),
        ).one()
        return {
            "location_count": int(row.location_count or 0),
            "stamping_supplier_count": int(row.stamping_supplier_count or 0),
            "vehicle_model_count": int(row.vehicle_model_count or 0),
            "part_number_count": int(row.part_number_count or 0),
            "version_count": int(row.version_count or 0),
        }

    def list_with_processes(
        self,
        db: Session,
        location: str,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[StampingPart]:
        """按基地等条件加载零件、工序与拼焊子片（加工费/零件核价用，不分页）"""
        from sqlalchemy.orm import selectinload

        q = db.query(StampingPart).filter(StampingPart.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPart.version == version)

        return (
            q.options(
                selectinload(StampingPart.processes),
                selectinload(StampingPart.tailor_weld_blanks),
            )
            .order_by(StampingPart.seq_no, StampingPart.id)
            .all()
        )

    def list_for_export(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
    ) -> List[StampingPart]:
        """按列表筛选加载零件 + 工序 + 拼焊子片（导出用，不分页）。"""
        from sqlalchemy.orm import selectinload

        q = self._build_list_query(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            part_name=part_name,
        )
        return (
            q.options(
                selectinload(StampingPart.processes),
                selectinload(StampingPart.tailor_weld_blanks),
            )
            .order_by(StampingPart.seq_no, StampingPart.id)
            .all()
        )

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[StampingPart]:
        return db.query(StampingPart).offset(skip).limit(limit).all()

    def create(self, db: Session, part_data: PartData) -> StampingPart:
        part = model_from_payload(StampingPart, part_data)
        db.add(part)
        db.commit()
        db.refresh(part)
        logger.info("创建零件: %s (id=%s)", part.part_number, part.id)
        return part

    def bulk_create(self, db: Session, parts_data: List[PartData]) -> List[StampingPart]:
        parts = [model_from_payload(StampingPart, data) for data in parts_data]
        db.add_all(parts)
        logger.info("批量创建零件: %s 个", len(parts))
        return parts

    def update(self, db: Session, part_id: int, update_data: StampingPartPatch) -> Optional[StampingPart]:
        part = self.get_by_id(db, part_id)
        if not part:
            return None
        apply_payload_fields(
            part,
            update_data,
            skip=frozenset({"id", "created_by", "created_at"}),
        )
        db.commit()
        db.refresh(part)
        logger.info("更新零件: id=%s", part_id)
        return part

    def delete(self, db: Session, part_id: int) -> bool:
        """删除零件（关联工序由调用方处理，或依赖数据库外键级联删除）"""
        part = self.get_by_id(db, part_id)
        if not part:
            return False
        db.delete(part)
        db.commit()
        logger.info(f"删除零件: id={part_id}")
        return True

    def get_all_by_scope(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
    ) -> List[StampingPart]:
        """按唯一范围键查询零件：基地 + 冲压工厂 + 车型 + 版本。"""
        return db.query(StampingPart).filter(
            StampingPart.location == location,
            StampingPart.stamping_supplier == stamping_supplier,
            StampingPart.vehicle_model == vehicle_model,
            StampingPart.version == version,
        ).all()

    def delete_by_scope(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
    ) -> int:
        """按基地 + 冲压工厂 + 车型 + 版本批量删除零件及工序。不提交事务。

        使用 bulk DELETE + flush，确保旧行在后续 INSERT 前已从库中消失，
        避免唯一键 (location, supplier, model, version, part_number) 冲突。
        """
        parts = self.get_all_by_scope(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        count = len(parts)
        if not parts:
            return 0

        part_ids = [part.id for part in parts]
        db.query(StampingProcess).filter(
            StampingProcess.part_id.in_(part_ids)
        ).delete(synchronize_session=False)
        db.query(StampingTailorWeldBlank).filter(
            StampingTailorWeldBlank.part_id.in_(part_ids)
        ).delete(synchronize_session=False)
        db.query(StampingPart).filter(
            StampingPart.id.in_(part_ids)
        ).delete(synchronize_session=False)
        db.flush()
        logger.info(
            "批量删除零件: %s/%s/%s/%s, 共 %s 个",
            location,
            stamping_supplier,
            vehicle_model,
            version,
            count,
        )
        return count

    def get_id_map_by_scope(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
    ) -> Dict[str, int]:
        """获取范围内零件号到 ID 的映射。"""
        parts = self.get_all_by_scope(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        return {p.part_number: p.id for p in parts if p.part_number}

    def count_processes_by_part_ids(self, db: Session, part_ids: List[int]) -> Dict[int, int]:
        """
        批量统计每个零件的工序数（一次 SQL, IN 子查询）。
        返回 {part_id: process_count}，缺省为 0。
        """
        if not part_ids:
            return {}
        rows = (
            db.query(StampingProcess.part_id, func.count(StampingProcess.id))
            .filter(StampingProcess.part_id.in_(part_ids))
            .group_by(StampingProcess.part_id)
            .all()
        )
        counts = {pid: cnt for pid, cnt in rows}
        return {pid: counts.get(pid, 0) for pid in part_ids}

    def get_filter_options(self, db: Session) -> StampingPartFilterOptionValues:
        """
        获取筛选下拉框的可选值。
        返回键名与 StampingPartListFilterOptions VO 对齐。
        """
        locations = (
            db.query(StampingPart.location)
            .distinct()
            .filter(StampingPart.location.isnot(None), StampingPart.location != "")
            .order_by(StampingPart.location)
            .all()
        )
        stamping_suppliers = (
            db.query(StampingPart.stamping_supplier)
            .distinct()
            .filter(StampingPart.stamping_supplier.isnot(None), StampingPart.stamping_supplier != "")
            .order_by(StampingPart.stamping_supplier)
            .all()
        )
        vehicle_models = (
            db.query(StampingPart.vehicle_model)
            .distinct()
            .filter(StampingPart.vehicle_model.isnot(None), StampingPart.vehicle_model != "")
            .order_by(StampingPart.vehicle_model)
            .all()
        )
        versions = (
            db.query(StampingPart.version)
            .distinct()
            .filter(StampingPart.version.isnot(None), StampingPart.version != "")
            .order_by(StampingPart.version)
            .all()
        )
        materials = (
            db.query(StampingPart.material)
            .distinct()
            .filter(StampingPart.material.isnot(None), StampingPart.material != "")
            .order_by(StampingPart.material)
            .all()
        )
        return {
            "locations": [r[0] for r in locations],
            "stamping_suppliers": [r[0] for r in stamping_suppliers],
            "vehicle_models": [r[0] for r in vehicle_models],
            "versions": [r[0] for r in versions],
            "materials": [r[0] for r in materials],
        }

    def get_cascade_filter_options(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        级联筛选选项：
        - 基地：全量
        - 冲压工厂：按基地过滤
        - 配套车型：按基地 + 冲压工厂过滤
        - 版本：按基地 + 冲压工厂 + 车型过滤
        """
        locations = self._distinct_string_values(db, StampingPart.location)

        supplier_q = db.query(StampingPart.stamping_supplier).distinct()
        if location:
            supplier_q = supplier_q.filter(StampingPart.location == location)
        stamping_suppliers = self._collect_distinct_strings(supplier_q, StampingPart.stamping_supplier)

        vehicle_q = db.query(StampingPart.vehicle_model).distinct()
        if location:
            vehicle_q = vehicle_q.filter(StampingPart.location == location)
        if stamping_supplier:
            vehicle_q = vehicle_q.filter(StampingPart.stamping_supplier == stamping_supplier)
        vehicle_models = self._collect_distinct_strings(vehicle_q, StampingPart.vehicle_model)

        version_q = db.query(StampingPart.version).distinct()
        if location:
            version_q = version_q.filter(StampingPart.location == location)
        if stamping_supplier:
            version_q = version_q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model:
            version_q = version_q.filter(StampingPart.vehicle_model == vehicle_model)
        versions = self._collect_distinct_strings(version_q, StampingPart.version)

        return {
            "locations": locations,
            "stamping_suppliers": stamping_suppliers,
            "vehicle_models": vehicle_models,
            "versions": versions,
        }

    def _distinct_string_values(
        self, db: Session, column: _StringColumn
    ) -> List[str]:
        query = (
            db.query(column)
            .distinct()
            .filter(column.isnot(None), column != "")
            .order_by(column)
        )
        values: List[str] = []
        for row in query.all():
            value = row[0]
            if isinstance(value, str) and value:
                values.append(value)
        return values

    def _collect_distinct_strings(
        self,
        query: Query[_T],
        column: _StringColumn,
    ) -> List[str]:
        rows = (
            query.filter(column.isnot(None), column != "")
            .order_by(column)
            .all()
        )
        values: List[str] = []
        for row in rows:
            if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
                continue
            value = row[0]
            if isinstance(value, str) and value:
                values.append(value)
        return values


    def list_parts_for_materials(
        self,
        db: Session,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[StampingPart]:
        """材料列表用：范围内有材质的零件（含拼焊子片）。"""
        from sqlalchemy.orm import selectinload

        q = db.query(StampingPart)
        if location:
            q = q.filter(StampingPart.location == location)
        if stamping_supplier:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version:
            q = q.filter(StampingPart.version == version)

        q = q.filter(
            StampingPart.material.isnot(None),
            StampingPart.material != "",
        )
        return (
            q.options(selectinload(StampingPart.tailor_weld_blanks))
            .order_by(StampingPart.material, StampingPart.seq_no, StampingPart.id)
            .all()
        )

    def _material_spec_filters(
        self,
        q: Query[_T],
        *,
        location: Optional[str],
        stamping_supplier: Optional[str],
        vehicle_model: Optional[str],
        version: Optional[str],
    ) -> Query[_T]:
        """材料规格查询共用的零件范围过滤。"""
        if location:
            q = q.filter(StampingPart.location == location)
        if stamping_supplier:
            q = q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model:
            q = q.filter(StampingPart.vehicle_model == vehicle_model)
        if version:
            q = q.filter(StampingPart.version == version)
        return q

    def _material_specs_union_query(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Subquery:
        """
        主表零件材质/料厚 ∪ 拼焊子片材质/料厚。

        拼焊总成主表常只落一段料厚（如 0.70），另一段只在子片上；
        钢价 Step1 必须把子片规格一并纳入去重。
        """
        part_q = self._material_spec_filters(
            db.query(
                StampingPart.location.label("location"),
                StampingPart.material.label("material"),
                StampingPart.thickness.label("thickness"),
            ),
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        ).filter(
            StampingPart.location.isnot(None),
            StampingPart.location != "",
            StampingPart.material.isnot(None),
            StampingPart.material != "",
            StampingPart.thickness.isnot(None),
        )

        blank_q = self._material_spec_filters(
            db.query(
                StampingPart.location.label("location"),
                StampingTailorWeldBlank.material.label("material"),
                StampingTailorWeldBlank.thickness.label("thickness"),
            ).join(
                StampingTailorWeldBlank,
                StampingTailorWeldBlank.part_id == StampingPart.id,
            ),
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        ).filter(
            StampingPart.location.isnot(None),
            StampingPart.location != "",
            StampingTailorWeldBlank.material.isnot(None),
            StampingTailorWeldBlank.material != "",
            StampingTailorWeldBlank.thickness.isnot(None),
        )

        return part_q.union(blank_q).subquery()

    def count_material_specs(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
    ) -> int:
        """统计去重后的材料+厚度规格行数（含拼焊子片）。"""
        combined = self._material_specs_union_query(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        return db.query(func.count()).select_from(combined).scalar() or 0

    def list_material_specs(
        self,
        db: Session,
        *,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
    ) -> List[MaterialSpecRow]:
        """
        列出去重后的 基地 + 材料(钢种) + 厚度（钢价计算 Step1）。

        含拼焊子片规格。必须带 location，避免跨基地材料串用。
        """
        combined = self._material_specs_union_query(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        rows = (
            db.query(combined.c.location, combined.c.material, combined.c.thickness)
            .order_by(
                combined.c.location,
                combined.c.material,
                combined.c.thickness,
            )
            .all()
        )
        return [
            {
                "location": r[0],
                "material": r[1],
                "thickness": r[2],
            }
            for r in rows
        ]
