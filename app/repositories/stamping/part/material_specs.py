"""钢价 Step1 用材料规格：主表 ∪ 拼焊子片。漏规格先查这里再查上传解析。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.sql.selectable import Subquery

from app.models.stamping import StampingPart, StampingTailorWeldBlank
from app.repositories.stamping.part.filters import _filter_supplier
from app.repositories.stamping.part.types import MaterialSpecRow


class StampingPartMaterialSpecs:
    def list_parts_for_materials(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[StampingPart]:
        """材料列表用：范围内有材质的零件（含拼焊子片）。"""
        from sqlalchemy.orm import selectinload

        q = db.query(StampingPart)
        if locations is not None:
            q = q.filter(StampingPart.location.in_(locations))
        elif location:
            q = q.filter(StampingPart.location == location)
        q = _filter_supplier(
            q,
            StampingPart.stamping_supplier,
            stamping_supplier,
            stamping_suppliers,
        )
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

    def _material_specs_union_query(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> Subquery:
        """
        主表零件材质/料厚 ∪ 拼焊子片材质/料厚。

        拼焊总成主表常只落一段料厚（如 0.70），另一段只在子片上。
        钢价 Step1 只按基地全量调 list_material_specs；统计可再按车型收窄。
        """
        location_clean = (location or "").strip() or None
        vehicle_clean = (vehicle_model or "").strip() or None

        part_q = db.query(
            StampingPart.location.label("location"),
            StampingPart.material.label("material"),
            StampingPart.thickness.label("thickness"),
        ).filter(
            StampingPart.material.isnot(None),
            StampingPart.material != "",
            StampingPart.thickness.isnot(None),
        )
        if location_clean:
            part_q = part_q.filter(StampingPart.location == location_clean)
        if vehicle_clean:
            part_q = part_q.filter(StampingPart.vehicle_model == vehicle_clean)

        blank_q = (
            db.query(
                StampingPart.location.label("location"),
                StampingTailorWeldBlank.material.label("material"),
                StampingTailorWeldBlank.thickness.label("thickness"),
            )
            .join(
                StampingTailorWeldBlank,
                StampingTailorWeldBlank.part_id == StampingPart.id,
            )
            .filter(
                StampingTailorWeldBlank.material.isnot(None),
                StampingTailorWeldBlank.material != "",
                StampingTailorWeldBlank.thickness.isnot(None),
            )
        )
        if location_clean:
            blank_q = blank_q.filter(StampingPart.location == location_clean)
        if vehicle_clean:
            blank_q = blank_q.filter(StampingPart.vehicle_model == vehicle_clean)

        return part_q.union(blank_q).subquery()

    def count_material_specs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> int:
        """统计去重后的材料+厚度规格行数（含拼焊子片）。"""
        combined = self._material_specs_union_query(
            db,
            location=location,
            vehicle_model=vehicle_model,
        )
        return db.query(func.count()).select_from(combined).scalar() or 0

    def list_distinct_spec_grades(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        """统计用：范围内去重牌号（含拼焊子片）。"""
        combined = self._material_specs_union_query(
            db,
            location=location,
            vehicle_model=vehicle_model,
        )
        rows = db.query(combined.c.material).distinct().order_by(combined.c.material).all()
        return [row[0] for row in rows if row[0]]

    def list_material_specs(self, db: Session, *, location: str) -> list[MaterialSpecRow]:
        """
        列出该基地去重后的 基地 + 材料(钢种) + 厚度（钢价计算 Step1）。

        含拼焊子片。覆盖该基地全部车型与冲压厂，避免按车型漏规格。
        """
        combined = self._material_specs_union_query(db, location=location)
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
