"""
SchemaCatalog：从现网 Pydantic VO 投影 LLM 可读的 schema_card。

设计对齐 docs/llm-costing-analysis-report-design.md §4.7：
- 键名与 VO 属性同源
- allowlist 裁剪，禁止整库 schema 灌进 Prompt
- 中文标签 = Field.description / 受控覆盖表
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from app.schemas.vo.bom_l0_welding_fee_vo import BomL0WeldingFeeVO
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO
from app.schemas.vo.l0_assembly_cost_vo import (
    L0AssemblyCostIndirectVO,
    L0AssemblyCostItemVO,
    L0AssemblyCostVO,
)
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostVO
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeVO
from app.schemas.vo.steel_price_vo import SteelPriceResponse
from app.services.llm.catalog.field_labels import (
    AGGREGATE_FIELD_LABELS,
    L0_FIELD_LABELS,
    MONEY_FIELD_NAMES,
    STEEL_PRICE_FIELD_LABELS,
    STAMPING_PART_COST_FIELD_LABELS,
)

# 默认合并覆盖表：调用方仍可再 overlay
_DEFAULT_LABEL_OVERRIDES: dict[str, str] = {
    **AGGREGATE_FIELD_LABELS,
    **STEEL_PRICE_FIELD_LABELS,
    **STAMPING_PART_COST_FIELD_LABELS,
    **L0_FIELD_LABELS,
}


def _merged_label_overrides(
    label_overrides: Mapping[str, str] | None,
) -> dict[str, str]:
    return {**_DEFAULT_LABEL_OVERRIDES, **(label_overrides or {})}


@dataclass(frozen=True, slots=True)
class SchemaFieldCard:
    """单个字段的 LLM 词典条目。"""

    name: str
    type_name: str
    label_zh: str
    description: str | None
    is_money: bool
    source_model: str


@dataclass(frozen=True, slots=True)
class SchemaCard:
    """一次注入 Prompt 的字段卡集合。"""

    fields: tuple[SchemaFieldCard, ...]
    model_names: tuple[str, ...]

    def field_names(self) -> frozenset[str]:
        return frozenset(field.name for field in self.fields)


def _annotation_type_name(annotation: object) -> str:
    if annotation is None:
        return "unknown"
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type):
            return annotation.__name__
        return str(annotation).replace("typing.", "")
    args = get_args(annotation)
    arg_names = ", ".join(_annotation_type_name(arg) for arg in args) if args else ""
    origin_name = getattr(origin, "__name__", str(origin))
    return f"{origin_name}[{arg_names}]" if arg_names else origin_name


def _field_description(field_info: FieldInfo) -> str | None:
    description = field_info.description
    if description is None:
        return None
    text = str(description).strip()
    return text or None


def _resolve_label(
    field_name: str,
    field_info: FieldInfo,
    label_overrides: Mapping[str, str],
) -> str:
    if field_name in label_overrides:
        return label_overrides[field_name]
    description = _field_description(field_info)
    if description:
        return description
    return field_name


def extract_model_fields(
    model: type[BaseModel],
    *,
    allowlist: frozenset[str] | None = None,
    label_overrides: Mapping[str, str] | None = None,
) -> list[SchemaFieldCard]:
    """从单个 Pydantic VO 抽取字段卡；allowlist 为空则导出全部字段。"""

    overrides = _merged_label_overrides(label_overrides)
    cards: list[SchemaFieldCard] = []
    model_name = model.__name__

    for field_name, field_info in model.model_fields.items():
        if allowlist is not None and field_name not in allowlist:
            continue
        cards.append(
            SchemaFieldCard(
                name=field_name,
                type_name=_annotation_type_name(field_info.annotation),
                label_zh=_resolve_label(field_name, field_info, overrides),
                description=_field_description(field_info),
                is_money=field_name in MONEY_FIELD_NAMES,
                source_model=model_name,
            )
        )
    return cards


def extract_aggregate_fields(
    field_names: Sequence[str],
    *,
    label_overrides: Mapping[str, str] | None = None,
) -> list[SchemaFieldCard]:
    """声明 Pack 聚合键（VO 没有的 *_sum / 计数等）。"""

    overrides = _merged_label_overrides(label_overrides)
    cards: list[SchemaFieldCard] = []
    for field_name in field_names:
        cards.append(
            SchemaFieldCard(
                name=field_name,
                type_name="aggregate",
                label_zh=overrides.get(field_name, field_name),
                description=overrides.get(field_name),
                is_money=field_name in MONEY_FIELD_NAMES,
                source_model="AggregatePack",
            )
        )
    return cards


def build_schema_card(
    models: Sequence[type[BaseModel]],
    *,
    allowlist: frozenset[str] | None = None,
    label_overrides: Mapping[str, str] | None = None,
    aggregate_fields: Sequence[str] = (),
) -> SchemaCard:
    """合并多个 VO + 可选聚合键，同名字段后者覆盖前者（便于覆盖表优先）。"""

    by_name: dict[str, SchemaFieldCard] = {}
    model_names: list[str] = []

    for model in models:
        model_names.append(model.__name__)
        for card in extract_model_fields(
            model,
            allowlist=allowlist,
            label_overrides=label_overrides,
        ):
            by_name[card.name] = card

    for card in extract_aggregate_fields(
        aggregate_fields,
        label_overrides=label_overrides,
    ):
        by_name[card.name] = card

    fields = tuple(sorted(by_name.values(), key=lambda item: item.name))
    return SchemaCard(fields=fields, model_names=tuple(model_names))


def format_schema_card_markdown(card: SchemaCard) -> str:
    """生成可注入 System Prompt 的 Markdown 词典。"""

    lines = [
        "【字段词典 — 只能使用下列字段名，禁止发明新字段】",
        f"来源 VO：{', '.join(card.model_names) if card.model_names else '（仅聚合键）'}",
        "",
    ]
    for field in card.fields:
        money_flag = " [金额·元]" if field.is_money else ""
        lines.append(
            f"- `{field.name}` ({field.type_name}){money_flag} = {field.label_zh}"
            f"  ← {field.source_model}"
        )
    lines.extend(
        [
            "",
            "【铁律】",
            "1. 报告中的英文字段名必须出现在上表。",
            "2. 金额单位为元；禁止改为万元，禁止 ÷10000。",
            "3. JSON 未给出的字段不得编造数值。",
        ]
    )
    return "\n".join(lines)


def format_schema_card_json_lines(card: SchemaCard) -> list[dict[str, str | bool]]:
    """结构化导出（测试 / 调试用），值类型收窄为可 JSON 化。"""

    rows: list[dict[str, str | bool]] = []
    for field in card.fields:
        rows.append(
            {
                "name": field.name,
                "type_name": field.type_name,
                "label_zh": field.label_zh,
                "is_money": field.is_money,
                "source_model": field.source_model,
            }
        )
    return rows


def project_mapping(
    payload: Mapping[str, object],
    allowed_names: frozenset[str],
) -> dict[str, object]:
    """按词典裁剪 dict，去掉未声明键，防止脏数据进 Prompt。"""

    return {
        key: value
        for key, value in payload.items()
        if key in allowed_names
    }


def project_mapping_deep(
    payload: object,
    allowed_names: frozenset[str],
) -> object:
    """
    递归裁剪：dict 只保留 allowlist 键；list 逐项处理。
    用于 Context Pack 根对象（含嵌套 monthOverview 等）。
    注意：嵌套 dict 的键同样受同一 allowlist 约束；
    若嵌套使用不同字段集，请对子对象单独 project。
    """

    if isinstance(payload, Mapping):
        return {
            key: project_mapping_deep(value, allowed_names)
            for key, value in payload.items()
            if key in allowed_names
        }
    if isinstance(payload, list):
        return [project_mapping_deep(item, allowed_names) for item in payload]
    return payload


# ---------------------------------------------------------------------------
# Pack 预设：实现侧一处维护（对齐设计 §4.7.4）
# ---------------------------------------------------------------------------

L0_DASHBOARD_ALLOWLIST: frozenset[str] = frozenset(
    {
        "year",
        "month",
        "location",
        "vehicle_model",
        "bom_version",
        "part_number",
        "part_name",
        "stamping_amount",
        "purchased_amount",
        "bundle_amount",
        "welding_amount",
        "welding_other_fee",
        "total_amount",
        "indirect_amount",
        "grand_total",
        "calc_status",
        "missing_leaf_count",
        "calc_message",
        "code",
        "label",
        "amount",
        "l0_count",
        "ok_count",
        "partial_count",
        "grand_total_sum",
        "total_amount_sum",
        "indirect_amount_sum",
        "steel_price_row_count",
        "stamping_part_cost_row_count",
        "status",
    }
)

L0_DASHBOARD_AGGREGATES: tuple[str, ...] = (
    "l0_count",
    "ok_count",
    "partial_count",
    "grand_total_sum",
    "total_amount_sum",
    "indirect_amount_sum",
    "steel_price_row_count",
    "stamping_part_cost_row_count",
    "status",
)

_ANNUAL_LABELS: dict[str, str] = {
    **L0_FIELD_LABELS,
    "stamping_supplier": "冲压工厂",
}


def build_pack_schema_card(pack_id: str) -> SchemaCard:
    """按 Pack ID 返回预绑定的 SchemaCard。"""

    if pack_id == "scope_meta":
        return build_schema_card(
            [],
            label_overrides=L0_FIELD_LABELS,
            aggregate_fields=(
                "location",
                "year",
                "month",
                "vehicle_model",
                "bom_version",
                "part_number",
                "l0_count",
                "hard_stop",
                "can_start",
                "message",
            ),
        )
    if pack_id in {"month_overview", "l0_top_drivers", "dashboard", "l0"}:
        return build_schema_card(
            [L0AssemblyCostVO, L0AssemblyCostIndirectVO],
            allowlist=L0_DASHBOARD_ALLOWLIST,
            label_overrides=L0_FIELD_LABELS,
            aggregate_fields=L0_DASHBOARD_AGGREGATES,
        )
    if pack_id == "l0_indirect_summary":
        return build_schema_card(
            [L0AssemblyCostIndirectVO],
            allowlist=frozenset({"code", "label", "amount", "rate", "base_amount"}),
            label_overrides=L0_FIELD_LABELS,
            aggregate_fields=("indirect_amount_sum",),
        )
    if pack_id == "missing_price_risk":
        return build_schema_card(
            [L0AssemblyCostVO],
            allowlist=frozenset(
                {
                    "part_number",
                    "part_name",
                    "calc_status",
                    "missing_leaf_count",
                    "calc_message",
                }
            ),
            label_overrides=L0_FIELD_LABELS,
            aggregate_fields=("partial_count",),
        )
    if pack_id == "mom_comparison":
        return build_schema_card(
            [],
            label_overrides=L0_FIELD_LABELS,
            aggregate_fields=(
                "year",
                "month",
                "l0_count",
                "grand_total_sum",
                "mom_delta",
                "mom_rate",
            ),
        )
    if pack_id in {"stamping_cost_summary", "stamping_part", "part_drilldown_stamping"}:
        return build_schema_card(
            [StampingPartCostVO],
            allowlist=frozenset(
                {
                    "year",
                    "month",
                    "location",
                    "stamping_supplier",
                    "vehicle_model",
                    "part_number",
                    "part_name",
                    "material",
                    "thickness",
                    "unit_cost",
                    "material_net_per_part",
                    "process_fee_amount",
                    "steel_mill",
                    "steel_ton_price",
                    "calc_status",
                    "calc_fail_reason",
                }
            ),
            label_overrides=STAMPING_PART_COST_FIELD_LABELS,
        )
    if pack_id in {"steel_price_summary", "steel"}:
        return build_schema_card(
            [SteelPriceResponse],
            allowlist=frozenset(
                {
                    "year",
                    "month",
                    "location",
                    "steel_mill",
                    "category_name",
                    "grade",
                    "thickness",
                    "width",
                    "spec",
                    "base_price",
                    "thickness_adjustment",
                    "width_adjustment",
                    "final_price_per_ton",
                    "audit_status",
                }
            ),
            label_overrides=STEEL_PRICE_FIELD_LABELS,
        )
    if pack_id in {"engine_gate_digest", "gate"}:
        return build_schema_card(
            [CostingEngineGateItemVO],
            label_overrides={
                "code": "门禁代码",
                "ok": "是否通过",
                "message": "说明",
                "navigate": "跳转信息",
            },
        )
    if pack_id == "annual_calc_digest":
        return build_schema_card(
            [StampingProcessFeeVO, BomL0WeldingFeeVO],
            allowlist=frozenset(
                {
                    "year",
                    "location",
                    "vehicle_model",
                    "part_number",
                    "part_name",
                    "stamping_supplier",
                    "audit_status",
                }
            ),
            label_overrides=_ANNUAL_LABELS,
        )
    if pack_id == "part_drilldown":
        return build_schema_card(
            [L0AssemblyCostVO, L0AssemblyCostItemVO],
            allowlist=frozenset(
                {
                    "part_number",
                    "part_name",
                    "grand_total",
                    "total_amount",
                    "stamping_amount",
                    "purchased_amount",
                    "bundle_amount",
                    "welding_amount",
                    "welding_other_fee",
                    "indirect_amount",
                    "calc_status",
                    "cost_source",
                    "unit_price",
                    "effective_qty",
                    "line_amount",
                    "level_label",
                }
            ),
            label_overrides=L0_FIELD_LABELS,
        )

    raise KeyError(f"未知 pack_id: {pack_id}")


def build_merged_pack_schema_card(pack_ids: Sequence[str]) -> SchemaCard:
    """合并多个 Pack 的字段卡（同名后者覆盖）。"""

    by_name: dict[str, SchemaFieldCard] = {}
    model_names: list[str] = []
    for pack_id in pack_ids:
        card = build_pack_schema_card(pack_id)
        for name in card.model_names:
            if name not in model_names:
                model_names.append(name)
        for field in card.fields:
            by_name[field.name] = field
    return SchemaCard(
        fields=tuple(sorted(by_name.values(), key=lambda item: item.name)),
        model_names=tuple(model_names),
    )


def schema_card_fingerprint(card: SchemaCard) -> str:
    """稳定短指纹，便于纳入 prompt_hash。"""

    import hashlib

    payload = "|".join(
        f"{field.name}:{field.type_name}:{field.label_zh}:{field.is_money}"
        for field in card.fields
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
