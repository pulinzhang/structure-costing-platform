"""核价引擎门禁：条目组装。"""

from __future__ import annotations

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.services.costing.engine.gate_navigate import build_navigate
from app.services.costing.engine.scope_discovery import DiscoveryResult

USABLE_STATUSES = [AUDIT_PENDING, AUDIT_APPROVED, AUDIT_REJECTED]
PERIOD_FILTERED_SKIP = "项目该月未覆盖，未展开此项检查"


def make_item(
    *,
    code: str,
    ok: bool,
    missing: list[str],
    message: str,
    location: str,
    year: int,
    month: int,
    with_navigate: bool | None = None,
) -> CostingEngineGateItemVO:
    # 默认：失败项带跳转；可强制给「软提示」也带 navigate
    attach_nav = (not ok) if with_navigate is None else with_navigate
    navigate = None
    if attach_nav:
        navigate = build_navigate(code, year=year, month=month, location=location)
    return CostingEngineGateItemVO(
        code=code,
        ok=ok,
        missing=missing,
        message=message,
        navigate=navigate,
    )


def make_skipped(
    *,
    code: str,
    message: str,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO:
    return make_item(
        code=code,
        ok=True,
        missing=[],
        message=message,
        location=location,
        year=year,
        month=month,
    )


def skip_if_period_filtered(
    discovery: DiscoveryResult,
    *,
    code: str,
    location: str,
    year: int,
    month: int,
) -> CostingEngineGateItemVO | None:
    if not discovery.is_period_filtered():
        return None
    return make_skipped(
        code=code,
        message=PERIOD_FILTERED_SKIP,
        location=location,
        year=year,
        month=month,
    )
