"""设计变更回滚工艺零件：删新零件及其工序，清空旧零件失效月。材料变更历史由调用方先删。只 flush。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import audit_update
from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.vo.user_vo import UserVO
from app.services.settings.foreign_key.service import ensure_deletable
from app.services.settings.logical_ref.service import ensure_logical_deletable


def rollback_engineering_change_part(
    part_repo: StampingPartRepository,
    process_repo: StampingProcessRepository,
    db: Session,
    *,
    after_part_id: int | None,
    before_part_id: int | None,
    current_user: UserVO,
) -> None:
    """删新零件及其工序，清空旧零件失效月。不删材料变更历史。只 flush。"""
    if after_part_id is not None:
        # 外键与逻辑引用分开。前者不读 logical_ref，后者不发现外键。
        ensure_deletable(
            db,
            "stamping_parts",
            [{"id": after_part_id}],
            subject="该冲压零件",
        )
        ensure_logical_deletable(
            db,
            "stamping_parts",
            [{"id": after_part_id}],
            subject="该冲压零件",
        )
        process_repo.delete_by_part_ids(db, [after_part_id])
        part_repo.delete(db, after_part_id)
    if before_part_id is not None:
        old_part = part_repo.get_by_id(db, before_part_id)
        if old_part is not None:
            old_part.expiry_year = None
            old_part.expiry_month = None
            old_part.updated_by = audit_update(current_user)["updated_by"]
    db.flush()
