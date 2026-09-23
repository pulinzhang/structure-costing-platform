"""engineering_change_material_effect_links 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.engineering_change.material_change.effect_link import (
    EngineeringChangeMaterialEffectLink,
)
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class MaterialChangeEffectLinkInsert:
    upload_log_id: int
    order_id: int
    effect_kind: str
    before_id: int
    after_id: int | None = None


class MaterialChangeEffectLinkRepository:
    def create(
        self, db: Session, payload: MaterialChangeEffectLinkInsert
    ) -> EngineeringChangeMaterialEffectLink:
        row = model_from_payload(EngineeringChangeMaterialEffectLink, payload)
        db.add(row)
        db.flush()
        return row

    def list_by_upload_log_id(
        self, db: Session, upload_log_id: int
    ) -> list[EngineeringChangeMaterialEffectLink]:
        return (
            db.query(EngineeringChangeMaterialEffectLink)
            .filter(EngineeringChangeMaterialEffectLink.upload_log_id == upload_log_id)
            .all()
        )

    def delete(self, db: Session, row: EngineeringChangeMaterialEffectLink) -> None:
        db.delete(row)
        db.flush()
