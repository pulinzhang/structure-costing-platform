"""EngineReadinessRunner：调用核价引擎 get_ready，输出确定性门禁快照。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.llm.scope_options_repository import ScopeOptionsRepository
from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.vo.costing_engine_vo import CostingEngineGateItemVO, CostingEngineReadyVO
from app.services.costing.engine.costing_engine_service import (
    SOFT_UPLOAD_GATE_CODES,
    CostingEngineService,
)
from app.services.llm.analysis.runner import AnalysisRunResult
from app.services.llm.analysis.shared.constants import ANALYSIS_VERSION

GATE_LABEL_ZH: dict[str, str] = {
    "stamping_process": "冲压工艺",
    "tonnage_price": "冲次单价",
    "welding_unit_price": "焊接单价",
    "bom_snapshot": "材料清单（BOM）",
    "annual_part_price": "年度零件价",
    "packaging_transport": "包装运输费",
    "base_price": "钢材基准价",
    "thickness_policy": "厚度加减价政策",
    "scrap_price": "废料月度销售价",
    "system_rates": "系统费率配置",
}


def _gate_to_dict(item: CostingEngineGateItemVO) -> dict[str, Any]:
    return {
        "code": item.code,
        "label": GATE_LABEL_ZH.get(item.code, item.code),
        "ok": item.ok,
        "hard_stop": (not item.ok) and item.code not in SOFT_UPLOAD_GATE_CODES,
        "soft_hint": item.code in SOFT_UPLOAD_GATE_CODES and bool(item.missing),
        "message": item.message,
        "missing": list(item.missing or []),
        "navigate_page": item.navigate.page if item.navigate else None,
        "navigate_label": item.navigate.label if item.navigate else None,
    }


def _ready_to_summary(ready: CostingEngineReadyVO) -> dict[str, Any]:
    gates = ready.gates.upload_or_config
    hard_fails = [g for g in gates if (not g.ok) and g.code not in SOFT_UPLOAD_GATE_CODES]
    soft_hints = [g for g in gates if g.code in SOFT_UPLOAD_GATE_CODES and (not g.ok or g.missing)]
    ok_items = [g for g in gates if g.ok and g.code not in SOFT_UPLOAD_GATE_CODES]
    l0_labels = [f"{s.vehicle_model}/{s.bom_version}" for s in ready.plan.l0_scopes]
    return {
        "kind": "engine_readiness",
        "location": ready.input.get("location"),
        "year": ready.input.get("year"),
        "month": ready.input.get("month"),
        "can_start": ready.can_start,
        "hard_stop": ready.gates.hard_stop,
        "hard_fail_count": len(hard_fails),
        "soft_hint_count": len(soft_hints),
        "ready_count": len(ok_items),
        "l0_scopes": l0_labels,
        "vehicle_models": [s.vehicle_model for s in ready.plan.part_cost_scopes],
    }


def render_engine_readiness_markdown(
    *,
    user_question: str,
    ready: CostingEngineReadyVO,
) -> str:
    """规则模板：与引擎页红灯一致，不依赖 LLM。"""
    location = str(ready.input.get("location") or "")
    year = int(ready.input.get("year") or 0)
    month = int(ready.input.get("month") or 0)
    ym = f"{year}年{month:02d}月"

    lines = [
        f"## {location} {ym} 核算就绪检查",
        "",
        (
            "**结论：可以启动自动核价**（与「核价 → 自动核价引擎 → 检查就绪」一致）。"
            if ready.can_start
            else f"**结论：尚有 {sum(1 for g in ready.gates.upload_or_config if not g.ok and g.code not in SOFT_UPLOAD_GATE_CODES)} 项硬门禁未过，暂不能启动。**"
        ),
        "",
        "> 说明：材料清单（BOM）按「基地 + 项目 + 版本」维护，**可跨年复用**，不要求每年重传。",
        "",
    ]

    hard_fails = [
        g
        for g in ready.gates.upload_or_config
        if (not g.ok) and g.code not in SOFT_UPLOAD_GATE_CODES
    ]
    soft_hints = [
        g
        for g in ready.gates.upload_or_config
        if g.code in SOFT_UPLOAD_GATE_CODES and (g.missing or not g.ok)
    ]
    ok_items = [
        g
        for g in ready.gates.upload_or_config
        if g.ok and not (g.code in SOFT_UPLOAD_GATE_CODES and g.missing)
    ]

    if hard_fails:
        lines.append("### 还缺（需补齐后才能核算）")
        lines.append("")
        for item in hard_fails:
            label = GATE_LABEL_ZH.get(item.code, item.code)
            lines.append(f"- **{label}**：{item.message}")
            for miss in (item.missing or [])[:5]:
                lines.append(f"  - {miss}")
        lines.append("")

    if soft_hints:
        lines.append("### 建议核对（不阻断启动）")
        lines.append("")
        for item in soft_hints:
            label = GATE_LABEL_ZH.get(item.code, item.code)
            lines.append(f"- {label}：{item.message}")
        lines.append("")

    if ok_items:
        lines.append("### 已就绪")
        lines.append("")
        for item in ok_items:
            label = GATE_LABEL_ZH.get(item.code, item.code)
            lines.append(f"- {label}：{item.message}")
        lines.append("")

    if ready.plan.l0_scopes:
        scopes = "、".join(f"{s.vehicle_model}/{s.bom_version}" for s in ready.plan.l0_scopes)
        lines.append(f"成品核价范围（BOM 含 L0）：{scopes}。")
        lines.append("")

    lines.append(
        "补齐红灯项后，请在 **核价 → 自动核价引擎** 选择基地与年月，点 **检查就绪** 再 **启动**。"
    )
    return "\n".join(lines).strip()


class EngineReadinessRunner:
    """对齐 CostingEngineService.get_ready，供 LLM 助理「还差什么才能核算」问句。"""

    def __init__(self) -> None:
        self._engine = CostingEngineService()
        self._scope_repo = ScopeOptionsRepository()

    def run(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        location = (query.location() or "").strip()
        if not location:
            location = self._infer_location(db, query.user_question) or ""

        tr = query.time_range
        year = tr.end_year
        month = tr.end_month
        span_note = ""
        if tr.start != tr.end:
            span_note = (
                f"问句时间跨度为 {tr.start}～{tr.end}，按截止月 {year}-{month:02d} 检查就绪。"
            )

        if not location:
            return AnalysisRunResult(
                comparability="unknown",
                has_data=False,
                data_message="请说明生产基地（如青岛），才能检查核算还差哪些上传数据",
                summary={"kind": "engine_readiness", "location_missing": True},
                result={"kind": "engine_readiness", "can_start": False},
            )

        ready = self._engine.get_ready(
            db,
            location=location,
            year=year,
            month=month,
        )
        gates_payload = [_gate_to_dict(g) for g in ready.gates.upload_or_config]
        hard_fails = [g for g in gates_payload if g["hard_stop"]]

        data_message = (
            f"{location} {year}年{month:02d}月可启动自动核价"
            if ready.can_start
            else f"{location} {year}年{month:02d}月尚有 {len(hard_fails)} 项硬门禁未过"
        )
        if span_note:
            data_message = f"{span_note} {data_message}"

        return AnalysisRunResult(
            comparability="unknown",
            has_data=True,
            data_message=data_message,
            summary=_ready_to_summary(ready),
            result={
                "kind": "engine_readiness",
                "can_start": ready.can_start,
                "hard_stop": ready.gates.hard_stop,
                "gates": gates_payload,
                "plan": ready.plan.model_dump(mode="json"),
            },
            evidence={
                "engine_ready": ready.model_dump(mode="json"),
                "bom_note": "材料清单按基地+项目+版本维护，不按年失效；绿灯表示已有含 L0 的快照。",
            },
            analysis_version=ANALYSIS_VERSION,
        )

    def _infer_location(self, db: Session, question: str) -> str | None:
        text = (question or "").strip()
        if not text:
            return None
        for loc in self._scope_repo.list_locations(db):
            if loc and loc in text:
                return loc
            label = f"{loc}基地"
            if label in text:
                return loc
        return None
