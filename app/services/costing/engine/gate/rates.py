"""核价引擎门禁：系统费率配置。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.settings.system.system_config_repository import SystemConfigRepository
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate.item import make_item


def check_system_rates(
    repo: SystemConfigRepository,
    db: Session,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    config = repo.get_singleton(db)
    if config is None:
        return make_item(
            code="system_rates",
            ok=False,
            missing=["系统配置单例不存在"],
            message="缺少系统费率等配置",
            location=location,
            year=year,
            month=month,
        )
    return make_item(
        code="system_rates",
        ok=True,
        missing=[],
        message="系统费率配置已就绪",
        location=location,
        year=year,
        month=month,
    )
