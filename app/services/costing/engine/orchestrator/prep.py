"""引擎开场：确认 Run 仍在。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.costing.costing_engine_run import CostingEngineRun
from app.repositories.costing.engine.costing_engine_run_repository import (
    CostingEngineRunRepository,
)
from app.services.costing.engine.orchestrator.errors import RunDeletedError


def ensure_run(
    run_repo: CostingEngineRunRepository,
    db: Session,
    run_id: int,
) -> CostingEngineRun:
    run = run_repo.get_by_id(db, run_id)
    if run is None:
        raise RunDeletedError(f"run {run_id} deleted")
    return run
