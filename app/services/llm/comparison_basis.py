"""可比口径映射（切片叶模块：query 与 analysis 都只向下依赖这里）。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import ComparisonBasis

_COMPARABILITY_LABEL_ZH = {
    "tight": "同口径可比",
    "loose": "口径可能变化",
    "unknown": "口径未校验",
}

_BASIS_LABEL_ZH = {
    "same_part_and_bom": "同一零件号 + 同一物料清单版本",
    "same_part_loose": "仅同一零件号（物料清单可能变化）",
}


def comparison_basis_label_zh(basis: ComparisonBasis) -> str:
    if basis.notes:
        return basis.notes
    return _BASIS_LABEL_ZH.get(basis.label, basis.label)


def default_comparison_basis(
    *,
    same_bom_version: bool = True,
) -> ComparisonBasis:
    if same_bom_version:
        return ComparisonBasis(
            same_part=True,
            same_bom_version=True,
            same_material=False,
            same_process=False,
            same_formula_version=False,
            label="same_part_and_bom",
            notes="同零件号+同 BOM 版本纳入趋势；材料/工艺未校验",
        )
    return ComparisonBasis(
        same_part=True,
        same_bom_version=False,
        label="same_part_loose",
        notes="仅同零件号；BOM 可能漂移，口径 loose",
    )


def resolve_comparability(basis: ComparisonBasis) -> str:
    if basis.same_part and basis.same_bom_version:
        return "tight"
    if basis.same_part:
        return "loose"
    return "unknown"
