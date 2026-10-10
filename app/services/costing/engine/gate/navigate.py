"""硬停门禁 code → 功能页深链映射（设计 §5.3.2）。"""

from __future__ import annotations

from collections.abc import Callable

from app.schemas.vo.costing_engine_vo import CostingEngineNavigateVO


def build_navigate(
    code: str,
    *,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
) -> CostingEngineNavigateVO | None:
    """按门禁 code 生成 navigate；未知 code 返回 None。"""
    builders: dict[str, Callable[[], CostingEngineNavigateVO]] = {
        "vehicle_model": lambda: _nav_vehicle_model(year=year, month=month, location=location),
        "vehicle_model_period": lambda: _nav_vehicle_model_period(location=location),
        "stamping_process": lambda: _nav_stamping_process(location=location),
        "tonnage_price": lambda: _nav_tonnage_price(location=location),
        "die_unit_price": lambda: _nav_die_unit_price(location=location),
        "welding_unit_price": lambda: _nav_welding_unit_price(year=year, location=location),
        "bom_snapshot": lambda: _nav_bom_snapshot(location=location),
        "annual_part_price": lambda: _nav_annual_part_price(year=year, location=location),
        "packaging_transport": lambda: _nav_packaging_transport(year=year, location=location),
        "base_price": lambda: _nav_base_price(year=year, month=month, location=location),
        "thickness_policy": _nav_thickness_policy,
        "width_policy": _nav_width_policy,
        "scrap_price": lambda: _nav_scrap_price(year=year, month=month, location=location),
        "system_rates": _nav_system_rates,
    }
    builder = builders.get(code)
    if builder is None:
        return None
    return builder()


def _query(
    *,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    include_year: bool = False,
    include_month: bool = False,
    include_location: bool = False,
) -> dict[str, str | int]:
    query: dict[str, str | int] = {}
    if include_year and year is not None:
        query["year"] = year
    if include_month and month is not None:
        query["month"] = month
    if include_location and location:
        query["location"] = location
    return query


def _nav_vehicle_model(
    *, year: int | None, month: int | None, location: str | None
) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="stamping-parts",
        label="去查看零件列表",
        query=_query(
            year=year,
            month=month,
            location=location,
            include_year=True,
            include_month=True,
            include_location=True,
        ),
        secondary_page="bom-structure",
        secondary_label="查看产品结构",
    )


def _nav_vehicle_model_period(*, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="vehicle-model-list",
        label="去项目列表",
        query=_query(location=location, include_location=True),
    )


def _nav_stamping_process(*, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="stamping-upload",
        label="去上传工艺",
        query=_query(location=location, include_location=True),
        secondary_page="stamping-parts",
        secondary_label="查看零件列表",
    )


def _nav_tonnage_price(*, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="stamping-tonnage-upload",
        label="去上传冲次单价",
        query=_query(location=location, include_location=True),
        secondary_page="stamping-tonnage",
        secondary_label="查看冲次单价列表",
    )


def _nav_die_unit_price(*, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="stamping-die-unit-price",
        label="去维护模具单价",
        query=_query(location=location, include_location=True),
    )


def _nav_welding_unit_price(*, year: int | None, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="bom-welding-unit-price-upload",
        label="去上传焊接单价",
        query=_query(year=year, location=location, include_year=True, include_location=True),
        secondary_page="bom-welding-unit-price",
        secondary_label="查看焊接单价列表",
    )


def _nav_bom_snapshot(*, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="bom-upload",
        label="去上传材料清单",
        query=_query(location=location, include_location=True),
        secondary_page="bom-material",
        secondary_label="查看材料清单",
    )


def _nav_annual_part_price(*, year: int | None, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="bom-annual-part-price-upload",
        label="去上传年度零件价",
        query=_query(year=year, location=location, include_year=True, include_location=True),
        secondary_page="bom-annual-part-price",
        secondary_label="查看年度零件价",
    )


def _nav_packaging_transport(*, year: int | None, location: str | None) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="bom-packaging-transport-fee-upload",
        label="去上传包装运输费",
        query=_query(year=year, location=location, include_year=True, include_location=True),
        secondary_page="bom-packaging-transport-fee",
        secondary_label="查看包装运输费",
    )


def _nav_base_price(
    *, year: int | None, month: int | None, location: str | None
) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="base-price-upload",
        label="去上传基准价",
        query=_query(
            year=year,
            month=month,
            location=location,
            include_year=True,
            include_month=True,
            include_location=True,
        ),
        secondary_page="base-price-download",
        secondary_label="查看基准价列表",
    )


def _nav_thickness_policy() -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="steel-price-policy-upload",
        label="去上传厚度加减价政策",
        query={},
        secondary_page="steel-price-policy-download",
        secondary_label="查看加减价政策",
    )


def _nav_width_policy() -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="steel-price-policy-upload",
        label="去上传宽度加减价政策",
        query={},
        secondary_page="steel-price-policy-download",
        secondary_label="查看加减价政策",
    )


def _nav_scrap_price(
    *, year: int | None, month: int | None, location: str | None
) -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="scrap-price",
        label="去维护废料月度价",
        query=_query(
            year=year,
            month=month,
            location=location,
            include_year=True,
            include_month=True,
            include_location=True,
        ),
    )


def _nav_system_rates() -> CostingEngineNavigateVO:
    return CostingEngineNavigateVO(
        page="settings",
        label="去系统设置",
        query={},
    )
