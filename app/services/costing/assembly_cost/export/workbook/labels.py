"""导出用中文标签与筛选摘要。"""

from app.common.audit import audit_status_label
from app.services.bom.procurement_object.labels import CONFIRM_LABELS, KIND_LABELS

CALC_STATUS_LABELS = {
    "ok": "正常",
    "partial": "部分",
    "failed": "失败",
}
_COST_SOURCE_LABELS = {
    "stamping": "冲压零件价",
    "annual": "年度零件价",
    "bundle": "一口价",
    "skipped_by_bundle": "一口价未计价",
    "missing": "缺价",
}


def object_kind_label(kind: str | None) -> str:
    if not kind:
        return ""
    return KIND_LABELS.get(kind, kind)


def tree_level_label(level: int | None) -> str:
    return f"第{int(level or 0)}层"


def cost_source_label(source: str | None) -> str:
    if not source:
        return ""
    return _COST_SOURCE_LABELS.get(source, source)


def match_hint_label(hint: str | None) -> str:
    if not hint:
        return ""
    prefix = "bundle_parent:"
    if hint.startswith(prefix):
        parent = hint[len(prefix) :].strip()
        return f"一口价父件 {parent}" if parent else "一口价父件"
    if hint == "multi_supplier_unit_cost":
        return "多家工厂单价不一致"
    return hint


def confirm_status_label(status: str | None) -> str:
    if not status:
        return ""
    return CONFIRM_LABELS.get(status, status)


def calc_status_label(status: str | None) -> str:
    if not status:
        return ""
    return CALC_STATUS_LABELS.get(status, status)


def export_filter_text(
    *,
    year: int | None,
    month: int | None,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    part_number: str | None,
    audit_status: str | None,
    calc_status: str | None,
    view: str | None = None,
) -> str:
    parts: list[str] = []
    if year:
        parts.append(f"{year}年")
    if month:
        parts.append(f"{month}月")
    if location:
        parts.append(location)
    if vehicle_model:
        parts.append(vehicle_model)
    if bom_version:
        parts.append(f"版本 {bom_version}")
    if part_number:
        parts.append(f"零件 {part_number}")
    if audit_status:
        parts.append(audit_status_label(audit_status))
    if calc_status:
        parts.append(calc_status_label(calc_status))
    if view == "procurement":
        parts.append("采购")
    elif view == "finance":
        parts.append("财务树根")
    return " · ".join(parts) if parts else "全部筛选"
