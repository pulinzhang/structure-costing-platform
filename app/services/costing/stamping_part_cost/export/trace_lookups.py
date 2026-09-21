"""按核算行批量加载钢材/废料/加工费溯源实体。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)


def load_trace_maps(
    db: Session,
    rows: list[Any],
    *,
    steel_price_repo: SteelPriceRepository,
    scrap_price_repo: StampingScrapPriceRepository,
    process_fee_repo: StampingProcessFeeRepository,
) -> tuple[dict[Any, Any], dict[Any, Any], dict[Any, Any]]:
    steel_ids = sorted({int(row.steel_price_id) for row in rows if row.steel_price_id is not None})
    steel_by_id = {steel.id: steel for steel in steel_price_repo.list_by_ids(db, steel_ids)}
    scrap_ids = sorted({int(row.scrap_price_id) for row in rows if row.scrap_price_id is not None})
    scrap_by_id = {scrap.id: scrap for scrap in scrap_price_repo.list_by_ids(db, scrap_ids)}
    fee_ids = sorted({int(row.process_fee_id) for row in rows if row.process_fee_id is not None})
    fee_by_id = {fee.id: fee for fee in process_fee_repo.list_by_ids(db, fee_ids)}
    return steel_by_id, scrap_by_id, fee_by_id
