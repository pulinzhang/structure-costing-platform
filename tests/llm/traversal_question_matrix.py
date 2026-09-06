"""按库内 Scope + 侧栏菜单生成 LLM 遍历问句（防回归 / 防笑话）。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.llm.scope_options_repository import ScopeOptionsRepository
from app.services.llm.menu_catalog import MENU_COVERAGE
from tests.llm.menu_question_matrix import MENU_QUESTION_CASES


@dataclass(frozen=True, slots=True)
class TraversalScope:
    """当前库内可用于问句的主 Scope。"""

    location: str
    location_label: str
    vehicle_model: str
    bom_version: str
    anchor_year: int
    anchor_month: int
    anchor_ym: str
    part_number: str
    alt_location: str | None
    trend_start_ym: str
    trend_end_ym: str


@dataclass(frozen=True, slots=True)
class TraversalCase:
    case_id: str
    category: str
    user_question: str
    expected_subject: str | None = None
    expected_hash_page: str | None = None
    time_start: str | None = None
    time_end: str | None = None
    compare_locations: tuple[str, ...] = ()
    expect_has_data: bool | None = None
    notes: str = ""


def _pick_scope(db: Session) -> TraversalScope:
    repo = ScopeOptionsRepository()
    locations = repo.list_locations(db)
    vehicles = repo.list_vehicle_models(db)
    bom_versions = repo.list_bom_versions(db)
    years = repo.list_years(db)

    location = "青岛" if "青岛" in locations else (locations[0] if locations else "青岛")
    location_label = f"{location}基地" if not location.endswith("基地") else location
    vehicle = vehicles[0] if vehicles else "T28"
    bom_version = bom_versions[0] if bom_versions else "D/00"
    year = 2025 if 2025 in years else (years[0] if years else 2025)

    row = (
        db.query(AssemblyCost.year, AssemblyCost.month)
        .filter(AssemblyCost.location == location)
        .order_by(AssemblyCost.year.desc(), AssemblyCost.month.desc())
        .first()
    )
    if row:
        anchor_year, anchor_month = int(row[0]), int(row[1])
    else:
        anchor_year, anchor_month = year, 1

    anchor_ym = f"{anchor_year:04d}-{anchor_month:02d}"

    part_row = (
        db.query(AssemblyCost.part_number)
        .filter(
            AssemblyCost.location == location,
            AssemblyCost.grand_total > 0,
        )
        .order_by(AssemblyCost.id.asc())
        .first()
    )
    part_number = str(part_row[0]) if part_row else "501006873AA"

    alt_location = next((loc for loc in locations if loc != location), None)

    trend_end_year, trend_end_month = anchor_year, anchor_month
    trend_start_month = max(1, trend_end_month - 5)
    trend_start_year = trend_end_year
    trend_start_ym = f"{trend_start_year:04d}-{trend_start_month:02d}"
    trend_end_ym = anchor_ym

    return TraversalScope(
        location=location,
        location_label=location_label,
        vehicle_model=vehicle,
        bom_version=bom_version,
        anchor_year=anchor_year,
        anchor_month=anchor_month,
        anchor_ym=anchor_ym,
        part_number=part_number,
        alt_location=alt_location,
        trend_start_ym=trend_start_ym,
        trend_end_ym=trend_end_ym,
    )


def build_traversal_cases(db: Session) -> list[TraversalCase]:
    scope = _pick_scope(db)
    ym_label = f"{scope.anchor_year}年{scope.anchor_month:02d}月"
    cases: list[TraversalCase] = []

    for menu_case in MENU_QUESTION_CASES:
        cases.append(
            TraversalCase(
                case_id=f"menu_{menu_case.hash_page}",
                category="menu",
                user_question=menu_case.user_question,
                expected_subject=menu_case.expected_subject,
                expected_hash_page=menu_case.hash_page,
                time_start=scope.anchor_ym,
                time_end=scope.anchor_ym,
                expect_has_data=(
                    False
                    if menu_case.expected_subject == "winning_thickness"
                    else True
                    if menu_case.status == "complete" and menu_case.expected_subject is not None
                    else None
                ),
                notes=menu_case.menu_label,
            )
        )

    for item in MENU_COVERAGE:
        if any(c.case_id == f"menu_{item.hash_page}" for c in cases):
            continue
        cases.append(
            TraversalCase(
                case_id=f"coverage_{item.hash_page}",
                category="menu",
                user_question=f"{scope.location_label}，{ym_label}，{item.menu_label}的情况。",
                expected_subject=item.subject,
                expected_hash_page=item.hash_page,
                time_start=scope.anchor_ym,
                time_end=scope.anchor_ym,
                expect_has_data=False if item.subject == "winning_thickness" else None,
                notes=item.notes,
            )
        )

    analysis_specs: list[tuple[str, str, str | None, str | None, str | None, bool | None]] = [
        (
            "l0_trend_range",
            f"{scope.location} {scope.vehicle_model} {scope.anchor_year}年"
            f"{scope.trend_start_ym.split('-')[1]}月到"
            f"{scope.anchor_month:02d}月成品成本趋势怎么样？",
            "l0",
            scope.trend_start_ym,
            scope.trend_end_ym,
            True,
        ),
        (
            "l0_drivers",
            f"{scope.location} {scope.anchor_year}年{scope.anchor_month}月 "
            f"{scope.vehicle_model} 成品成本动因有哪些？",
            "l0",
            scope.anchor_ym,
            scope.anchor_ym,
            True,
        ),
        (
            "l0_summary",
            f"{scope.location} {scope.vehicle_model} {ym_label}核算情况怎么样？",
            "cost_total",
            scope.anchor_ym,
            scope.anchor_ym,
            True,
        ),
        (
            "l0_risk",
            f"{scope.location} {scope.vehicle_model} "
            f"{scope.anchor_year}年{scope.anchor_month}月成品核价缺价风险",
            "l0",
            scope.anchor_ym,
            scope.anchor_ym,
            True,
        ),
        (
            "l0_drilldown",
            f"{scope.location} {scope.part_number} {scope.anchor_year}年为什么涨了？",
            "part",
            f"{scope.anchor_year:04d}-01",
            f"{scope.anchor_year:04d}-12",
            True,
        ),
        (
            "l0_month_compare",
            f"{scope.location} {scope.vehicle_model} "
            f"{scope.anchor_year}年1月与{scope.anchor_month}月成品成本对比",
            "l0",
            scope.anchor_ym,
            scope.anchor_ym,
            True,
        ),
        (
            "steel_trend",
            f"{scope.location} {scope.anchor_year}年钢材联动价趋势",
            "steel_price",
            f"{scope.anchor_year:04d}-01",
            scope.anchor_ym,
            True,
        ),
        (
            "stamping_part",
            f"{scope.location} {scope.anchor_year}年{scope.anchor_month}月冲压件成本情况",
            "stamping_part",
            scope.anchor_ym,
            scope.anchor_ym,
            True,
        ),
        (
            "blind_summary",
            f"{scope.location_label} {ym_label}成本情况怎么样？",
            "cost_total",
            scope.anchor_ym,
            scope.anchor_ym,
            True,
        ),
        (
            "part_short_code",
            f"冲压件，8898，在{scope.location}存在吗？",
            "part",
            scope.anchor_ym,
            scope.anchor_ym,
            None,
        ),
    ]
    for case_id, question, subject, start, end, expect_data in analysis_specs:
        cases.append(
            TraversalCase(
                case_id=case_id,
                category="analysis",
                user_question=question,
                expected_subject=subject,
                time_start=start,
                time_end=end,
                expect_has_data=expect_data,
            )
        )

    if scope.alt_location:
        cases.append(
            TraversalCase(
                case_id="l0_compare_loc",
                category="analysis",
                user_question=(
                    f"{scope.location}和{scope.alt_location} "
                    f"{scope.anchor_year}年{scope.anchor_month}月成品成本对比"
                ),
                expected_subject="l0",
                time_start=scope.anchor_ym,
                time_end=scope.anchor_ym,
                compare_locations=(scope.location, scope.alt_location),
                expect_has_data=True,
            )
        )

    usage_specs = [
        ("usage_upload", "怎么上传冲压工艺文件？", "usage_help"),
        ("usage_engine", "自动核价引擎怎么用？", "usage_help"),
        ("usage_export", "成品核价一览怎么导出 Excel？", "usage_help"),
    ]
    for case_id, question, subject in usage_specs:
        cases.append(
            TraversalCase(
                case_id=case_id,
                category="usage",
                user_question=question,
                expected_subject=subject,
                expect_has_data=True,
            )
        )

    temporal_specs = [
        (
            "guard_year_in_menu",
            f"{scope.location_label}，{scope.anchor_year}年{scope.anchor_month:02d}月，成品成本的情况。",
        ),
        (
            "guard_ym_hyphen",
            f"{scope.location} {scope.anchor_year}-{scope.anchor_month:02d} 采购成本",
        ),
        (
            "guard_year_trend",
            f"{scope.location} {scope.vehicle_model} {scope.anchor_year}年近6个月趋势",
        ),
    ]
    for case_id, question in temporal_specs:
        cases.append(
            TraversalCase(
                case_id=case_id,
                category="guard",
                user_question=question,
                expected_subject=None,
                time_start=scope.anchor_ym,
                time_end=scope.anchor_ym,
                notes="不得把年份/年月识别为零件号",
            )
        )

    return cases


def mock_extractor_draft(case: TraversalCase, scope: TraversalScope) -> dict:
    """遍历测试用：模拟 LLM 条件抽取，时间与库内 Scope 对齐。"""
    if case.category == "usage":
        return {}
    start = case.time_start or scope.anchor_ym
    end = case.time_end or scope.anchor_ym
    filters: dict[str, str] = {"location": scope.location_label}
    if case.expected_subject in ("l0", "cost_total", "stamping_part"):
        filters["vehicle_model"] = scope.vehicle_model
    draft: dict = {
        "time_range": {"start": start, "end": end},
        "filters": filters,
        "compare_locations": list(case.compare_locations),
    }
    return draft


def load_traversal_cases() -> list[TraversalCase]:
    from app.database import DatabaseConfig

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        return build_traversal_cases(db)
    finally:
        db.close()
