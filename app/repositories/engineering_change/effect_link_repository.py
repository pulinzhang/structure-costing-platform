"""engineering_change_effect_links 数据访问。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.engineering_change.effect_link import EngineeringChangeEffectLink
from app.repositories.persist import model_from_payload


@dataclass(slots=True)
class EngineeringChangeEffectLinkInsert:
    change_order_id: int
    effect_kind: str
    before_id: int | None
    after_id: int | None
    sort_no: int
    upload_log_id: int = 0


class EngineeringChangeEffectLinkRepository:
    """效果链接 CRUD / 查询。"""

    def list_by_upload_log_id_desc(
        self, db: Session, upload_log_id: int
    ) -> list[EngineeringChangeEffectLink]:
        return (
            db.query(EngineeringChangeEffectLink)
            .filter(EngineeringChangeEffectLink.upload_log_id == upload_log_id)
            .order_by(EngineeringChangeEffectLink.sort_no.desc())
            .all()
        )

    def create(
        self, db: Session, payload: EngineeringChangeEffectLinkInsert
    ) -> EngineeringChangeEffectLink:
        row = model_from_payload(EngineeringChangeEffectLink, payload)
        db.add(row)
        db.flush()
        return row

    def delete_by_upload_log_id(self, db: Session, upload_log_id: int) -> int:
        deleted = (
            db.query(EngineeringChangeEffectLink)
            .filter(EngineeringChangeEffectLink.upload_log_id == upload_log_id)
            .delete(synchronize_session=False)
        )
        db.flush()
        return int(deleted)

    def bulk_create(
        self, db: Session, payloads: list[EngineeringChangeEffectLinkInsert]
    ) -> list[EngineeringChangeEffectLink]:
        rows = [model_from_payload(EngineeringChangeEffectLink, item) for item in payloads]
        for row in rows:
            db.add(row)
        db.flush()
        return rows
