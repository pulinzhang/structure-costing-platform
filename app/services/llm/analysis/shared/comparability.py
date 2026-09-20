"""B.5 可比口径：根据事实数据动态判定 tight / loose。"""

from __future__ import annotations

from collections import defaultdict

from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
from app.schemas.llm.analysis_query import ComparisonBasis
from app.services.llm.comparison_basis import resolve_comparability


def resolve_runtime_comparability(
    *,
    basis: ComparisonBasis,
    part_rows: list[L0PartPeriodRow] | None = None,
) -> tuple[str, str | None]:
    """在静态 basis 之上，用 BOM 漂移等事实收紧 comparability。"""
    static = resolve_comparability(basis)
    if not part_rows:
        return static, None

    if basis.same_bom_version:
        by_part: dict[str, set[str]] = defaultdict(set)
        for row in part_rows:
            by_part[row.part_number].add(row.bom_version)
        drift_parts = [
            part_number for part_number, versions in by_part.items() if len(versions) > 1
        ]
        if drift_parts:
            sample = ", ".join(drift_parts[:3])
            suffix = "…" if len(drift_parts) > 3 else ""
            return (
                "loose",
                f"同零件跨月存在多个 BOM 版本（如 {sample}{suffix}），不得宣称纯价格上涨",
            )

    if static == "tight" and basis.notes:
        return static, basis.notes
    return static, basis.notes
