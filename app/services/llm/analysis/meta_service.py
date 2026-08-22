"""
基础资料：Repository 从结果表 DISTINCT。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.llm.scope_options_repository import ScopeOptionsRepository
from app.schemas.vo.llm_analysis_vo import LlmScopeOptionsVO


class LlmMetaService:
    def __init__(self) -> None:
        self._scope_repo = ScopeOptionsRepository()

    def get_scope_options(self, db: Session) -> LlmScopeOptionsVO:
        return LlmScopeOptionsVO(
            locations=self._scope_repo.list_locations(db),
            vehicle_models=self._scope_repo.list_vehicle_models(db),
            bom_versions=self._scope_repo.list_bom_versions(db),
            years=self._scope_repo.list_years(db),
        )

    def list_known_locations(self, db: Session) -> list[str]:
        return self.get_scope_options(db).locations
