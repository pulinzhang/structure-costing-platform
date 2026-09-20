"""冲压工艺导入：材质与基价同一套 match_by_grade_key 改写。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.tailor_weld import (
    TailorWeldAssemblyParsed,
    TailorWeldBlankParsed,
)
from app.services.masterdata.steel_grade_category.steel_grade_category_service import (
    SteelGradeCategoryService,
)


def canonicalize_materials(
    db: Session,
    parts: list[Part],
    assemblies: list[TailorWeldAssemblyParsed],
) -> None:
    holders: list[Part | TailorWeldAssemblyParsed | TailorWeldBlankParsed] = [*parts]
    for assembly in assemblies:
        holders.append(assembly)
        holders.extend(assembly.blanks)
    bound = SteelGradeCategoryService().bind_stored_grades(
        db,
        [holder.material for holder in holders],
    )
    for holder, grade in zip(holders, bound, strict=True):
        holder.material = grade
