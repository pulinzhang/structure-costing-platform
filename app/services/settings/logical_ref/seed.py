"""启动时补还没有的逻辑引用。已有配置留下，不另建表。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.settings.logical_ref.repository import LogicalRefRepository
from app.services.settings.logical_ref.seeds.material_change import rows as material_change_rows
from app.services.settings.logical_ref.seeds.stamping_parts import rows as stamping_part_rows


def ensure_logical_ref_seed(db: Session) -> None:
    repository = LogicalRefRepository()
    for head, filters in (stamping_part_rows(), material_change_rows()):
        repository.insert_if_absent(db, head, filters)
    db.commit()
