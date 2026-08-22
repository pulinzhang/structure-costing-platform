"""
LlmContextAggregator：只调上游 Service 组装 Context Pack。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostQuery
from app.schemas.dto.steel_price_dto import SteelPriceQuery
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostQuery
from app.schemas.vo.l0_assembly_cost_vo import L0AssemblyCostVO
from app.services.costing.engine.costing_engine_service import CostingEngineService
from app.services.costing.l0_assembly_cost.l0_assembly_cost_service import (
    L0AssemblyCostService,
)
from app.services.costing.steel_price.steel_price_service import SteelPriceService
from app.services.costing.stamping_part_cost.stamping_part_cost_service import (
    StampingPartCostService,
)
from app.services.llm.catalog import (
    build_merged_pack_schema_card,
    format_schema_card_markdown,
)
from app.services.llm.context.pack_catalog import (
    L0_FETCH_LIMIT,
    MISSING_SAMPLE_LIMIT,
    STEEL_FETCH_LIMIT,
    STAMPING_FETCH_LIMIT,
    TOP_N,
    pack_ids_for,
)
from app.services.llm.context.packs._helpers import (
    decimal_sum,
    money_str,
    pick,
    previous_month,
    vo_dump,
)


@dataclass(frozen=True, slots=True)
class AnalysisScope:
    location: str
    year: int
    month: int
    vehicle_model: str
    bom_version: str
    part_number: str | None = None
    stamping_supplier: str | None = None
    engine_run_id: int | None = None


@dataclass(frozen=True, slots=True)
class AggregatedContext:
    report_type: str
    pack_ids: tuple[str, ...]
    context: dict[str, Any]
    schema_card_markdown: str
    has_data: bool
    data_message: str
    attachments: dict[str, Any]


class LlmContextAggregator:
    def __init__(self) -> None:
        self._l0 = L0AssemblyCostService()
        self._steel = SteelPriceService()
        self._stamping = StampingPartCostService()
        self._engine = CostingEngineService()

    def build(
        self,
        db: Session,
        *,
        report_type: str,
        scope: AnalysisScope,
    ) -> AggregatedContext:
        pack_ids = pack_ids_for(report_type)
        l0_rows = self._fetch_l0(db, scope)
        prev_year, prev_month = previous_month(scope.year, scope.month)
        prev_scope = AnalysisScope(
            location=scope.location,
            year=prev_year,
            month=prev_month,
            vehicle_model=scope.vehicle_model,
            bom_version=scope.bom_version,
            stamping_supplier=scope.stamping_supplier,
        )
        prev_l0 = (
            self._fetch_l0(db, prev_scope)
            if "mom_comparison" in pack_ids
            else []
        )

        packs: dict[str, Any] = {}
        for pack_id in pack_ids:
            packs[pack_id] = self._build_pack(
                db,
                pack_id=pack_id,
                scope=scope,
                l0_rows=l0_rows,
                prev_l0=prev_l0,
                report_type=report_type,
            )

        has_data = len(l0_rows) > 0
        data_message = (
            f"已加载 L0={len(l0_rows)}，"
            f"ok={sum(1 for r in l0_rows if r.calc_status == 'ok')}，"
            f"partial={sum(1 for r in l0_rows if r.calc_status == 'partial')}"
            if l0_rows
            else "当前 scope 无 L0 核价结果"
        )
        if report_type == "steel":
            steel_pack = packs.get("steel_price_summary") or {}
            has_data = int(steel_pack.get("row_count") or 0) > 0
            data_message = f"钢材联动价行数={steel_pack.get('row_count') or 0}"
        elif report_type == "stamping_part":
            stamp_pack = packs.get("stamping_cost_summary") or {}
            has_data = int(stamp_pack.get("row_count") or 0) > 0
            data_message = f"冲压零件价行数={stamp_pack.get('row_count') or 0}"
        elif report_type == "gate":
            gate = packs.get("engine_gate_digest") or {}
            has_data = True
            data_message = str(gate.get("message") or "已加载引擎门禁")

        meta = {
            "scope": {
                "location": scope.location,
                "year": scope.year,
                "month": scope.month,
                "vehicle_model": scope.vehicle_model,
                "bom_version": scope.bom_version,
                "part_number": scope.part_number,
                "stamping_supplier": scope.stamping_supplier,
            },
            "report_type": report_type,
            "hasData": has_data,
            "dataMessage": data_message,
            "generatedAt": now().isoformat(),
            "currencyNote": "金额单位：元/件（单车用量已计入）；禁止改为万元",
        }

        # 外壳 camelCase；业务键对齐 VO snake_case
        context: dict[str, Any] = {"meta": meta}
        key_map = {
            "scope_meta": "scopeMeta",
            "month_overview": "monthOverview",
            "l0_top_drivers": "l0TopDrivers",
            "l0_indirect_summary": "l0IndirectSummary",
            "missing_price_risk": "missingPriceRisk",
            "mom_comparison": "momComparison",
            "steel_price_summary": "steelPriceSummary",
            "stamping_cost_summary": "stampingCostSummary",
            "engine_gate_digest": "engineGateDigest",
            "part_drilldown": "partDrilldown",
        }
        for pack_id, payload in packs.items():
            context[key_map.get(pack_id, pack_id)] = payload

        schema_card = build_merged_pack_schema_card(list(pack_ids))
        # 对叶子 dict 做 allowlist 裁剪（meta 保留）
        allowed = schema_card.field_names() | frozenset(
            {
                "scope",
                "report_type",
                "hasData",
                "dataMessage",
                "generatedAt",
                "currencyNote",
                "breakdown",
                "by_grand_total",
                "items",
                "reason_counts",
                "missing_part_numbers_sample",
                "gates",
                "hard_stop",
                "message",
                "row_count",
                "top_by_final_price",
                "top_by_unit_cost",
                "current",
                "previous",
                "delta",
                "location",
                "year",
                "month",
                "vehicle_model",
                "bom_version",
                "part_number",
                "stamping_supplier",
                "ok",
                "code",
                "label",
                "navigate",
                "page",
                "query",
                "missing",
                "stamping_amount",
                "purchased_amount",
                "bundle_amount",
                "welding_amount",
                "welding_other_fee",
                "indirect_amount_sum",
                "grand_total_sum",
                "total_amount_sum",
                "l0_count",
                "ok_count",
                "partial_count",
                "status",
                "grand_total",
                "total_amount",
                "calc_status",
                "part_name",
                "amount",
                "rate",
                "base_amount",
                "mom_delta",
                "mom_rate",
                "final_price_per_ton",
                "unit_cost",
                "material_net_per_part",
                "process_fee_amount",
                "steel_mill",
                "grade",
                "thickness",
                "width",
                "spec",
                "category_name",
                "can_start",
            }
        )
        # 不强制深裁 meta；对业务 pack 值做浅层 project
        for camel_key, value in list(context.items()):
            if camel_key == "meta":
                continue
            if isinstance(value, dict):
                context[camel_key] = self._project_tree(value, allowed)

        attachments: dict[str, Any] = {}
        month_overview = packs.get("month_overview")
        if isinstance(month_overview, dict):
            attachments["month_overview_kpis"] = {
                "l0_count": month_overview.get("l0_count"),
                "grand_total_sum": month_overview.get("grand_total_sum"),
                "total_amount_sum": month_overview.get("total_amount_sum"),
                "indirect_amount_sum": month_overview.get("indirect_amount_sum"),
            }
        top = packs.get("l0_top_drivers")
        if isinstance(top, dict) and top.get("by_grand_total"):
            attachments["top_l0_by_grand_total"] = top.get("by_grand_total")

        return AggregatedContext(
            report_type=report_type,
            pack_ids=pack_ids,
            context=context,
            schema_card_markdown=format_schema_card_markdown(schema_card),
            has_data=has_data,
            data_message=data_message,
            attachments=attachments,
        )

    def context_to_json(self, context: dict[str, Any]) -> str:
        return json.dumps(context, ensure_ascii=False, indent=2)

    def _project_tree(
        self,
        payload: object,
        allowed: frozenset[str],
    ) -> object:
        if isinstance(payload, dict):
            out: dict[str, object] = {}
            for key, value in payload.items():
                if key in allowed or key in {
                    "breakdown",
                    "by_grand_total",
                    "items",
                    "gates",
                    "top_by_final_price",
                    "top_by_unit_cost",
                    "current",
                    "previous",
                    "delta",
                    "reason_counts",
                    "missing_part_numbers_sample",
                    "navigate",
                }:
                    out[key] = self._project_tree(value, allowed)
            return out
        if isinstance(payload, list):
            return [self._project_tree(item, allowed) for item in payload]
        return payload

    def _fetch_l0(
        self, db: Session, scope: AnalysisScope
    ) -> list[L0AssemblyCostVO]:
        rows, _total, _filters = self._l0.paginate(
            db,
            L0AssemblyCostQuery(
                year=scope.year,
                month=scope.month,
                location=scope.location,
                vehicle_model=scope.vehicle_model,
                bom_version=scope.bom_version,
                skip=0,
                limit=L0_FETCH_LIMIT,
            ),
        )
        return list(rows)

    def _build_pack(
        self,
        db: Session,
        *,
        pack_id: str,
        scope: AnalysisScope,
        l0_rows: list[L0AssemblyCostVO],
        prev_l0: list[L0AssemblyCostVO],
        report_type: str,
    ) -> Any:
        if pack_id == "scope_meta":
            return self._pack_scope_meta(db, scope, l0_rows)
        if pack_id == "month_overview":
            return self._pack_month_overview(l0_rows)
        if pack_id == "l0_top_drivers":
            return self._pack_l0_top(l0_rows)
        if pack_id == "l0_indirect_summary":
            return self._pack_indirect(l0_rows)
        if pack_id == "missing_price_risk":
            return self._pack_missing(l0_rows)
        if pack_id == "mom_comparison":
            return self._pack_mom(l0_rows, prev_l0, scope)
        if pack_id == "steel_price_summary":
            return self._pack_steel(db, scope)
        if pack_id == "stamping_cost_summary":
            return self._pack_stamping(db, scope)
        if pack_id == "engine_gate_digest":
            return self._pack_gate(db, scope)
        if pack_id == "part_drilldown":
            return self._pack_part_drilldown(db, scope, l0_rows)
        return None

    def _pack_scope_meta(
        self,
        db: Session,
        scope: AnalysisScope,
        l0_rows: list[L0AssemblyCostVO],
    ) -> dict[str, Any]:
        ready = self._engine.get_ready(
            db,
            location=scope.location,
            year=scope.year,
            month=scope.month,
        )
        return {
            "location": scope.location,
            "year": scope.year,
            "month": scope.month,
            "vehicle_model": scope.vehicle_model,
            "bom_version": scope.bom_version,
            "part_number": scope.part_number,
            "l0_count": len(l0_rows),
            "hard_stop": bool(ready.gates.hard_stop),
            "can_start": bool(ready.can_start),
            "message": (
                "引擎硬停，请先补齐主数据"
                if ready.gates.hard_stop
                else ("可启动核价" if ready.can_start else "门禁未完全通过")
            ),
        }

    def _pack_month_overview(self, rows: list[L0AssemblyCostVO]) -> dict[str, Any]:
        ok_count = sum(1 for row in rows if row.calc_status == "ok")
        partial_count = sum(1 for row in rows if row.calc_status == "partial")
        return {
            "l0_count": len(rows),
            "ok_count": ok_count,
            "partial_count": partial_count,
            "total_amount_sum": money_str(decimal_sum([r.total_amount for r in rows])),
            "grand_total_sum": money_str(decimal_sum([r.grand_total for r in rows])),
            "indirect_amount_sum": money_str(
                decimal_sum([r.indirect_amount for r in rows])
            ),
            "breakdown": {
                "stamping_amount": money_str(
                    decimal_sum([r.stamping_amount for r in rows])
                ),
                "purchased_amount": money_str(
                    decimal_sum([r.purchased_amount for r in rows])
                ),
                "bundle_amount": money_str(
                    decimal_sum([r.bundle_amount for r in rows])
                ),
                "welding_amount": money_str(
                    decimal_sum([r.welding_amount for r in rows])
                ),
                "welding_other_fee": money_str(
                    decimal_sum([r.welding_other_fee for r in rows])
                ),
            },
        }

    def _pack_l0_top(self, rows: list[L0AssemblyCostVO]) -> dict[str, Any]:
        ranked = sorted(rows, key=lambda r: r.grand_total, reverse=True)[:TOP_N]
        return {
            "by_grand_total": [
                {
                    "part_number": row.part_number,
                    "part_name": row.part_name,
                    "grand_total": money_str(row.grand_total),
                    "total_amount": money_str(row.total_amount),
                    "status": row.calc_status,
                    "calc_status": row.calc_status,
                }
                for row in ranked
            ]
        }

    def _pack_indirect(self, rows: list[L0AssemblyCostVO]) -> dict[str, Any]:
        by_code: dict[str, dict[str, Any]] = {}
        for row in rows:
            for item in row.indirects:
                bucket = by_code.get(item.code)
                if bucket is None:
                    by_code[item.code] = {
                        "code": item.code,
                        "label": item.label,
                        "amount": item.amount,
                    }
                else:
                    bucket["amount"] = bucket["amount"] + item.amount
        items = [
            {
                "code": code,
                "label": str(data["label"]),
                "amount": money_str(data["amount"]),
            }
            for code, data in sorted(by_code.items(), key=lambda kv: kv[0])
        ]
        return {
            "items": items,
            "indirect_amount_sum": money_str(
                decimal_sum([r.indirect_amount for r in rows])
            ),
        }

    def _pack_missing(self, rows: list[L0AssemblyCostVO]) -> dict[str, Any]:
        partial_rows = [row for row in rows if row.calc_status != "ok"]
        samples = [
            {
                "part_number": row.part_number,
                "part_name": row.part_name,
                "calc_status": row.calc_status,
                "missing_leaf_count": row.missing_leaf_count,
                "calc_message": row.calc_message,
            }
            for row in partial_rows[:MISSING_SAMPLE_LIMIT]
        ]
        reason_counts: dict[str, int] = {}
        for row in partial_rows:
            key = (row.calc_message or row.calc_status or "unknown").strip()[:80]
            reason_counts[key] = reason_counts.get(key, 0) + 1
        return {
            "partial_count": len(partial_rows),
            "missing_part_numbers_sample": samples,
            "reason_counts": reason_counts,
        }

    def _pack_mom(
        self,
        current: list[L0AssemblyCostVO],
        previous: list[L0AssemblyCostVO],
        scope: AnalysisScope,
    ) -> dict[str, Any] | None:
        if not previous:
            return None
        cur_sum = decimal_sum([r.grand_total for r in current])
        prev_sum = decimal_sum([r.grand_total for r in previous])
        delta = cur_sum - prev_sum
        rate = None
        if prev_sum != 0:
            rate = (delta / prev_sum).quantize(Decimal("0.0001"))
        prev_year, prev_month = previous_month(scope.year, scope.month)
        return {
            "current": {
                "year": scope.year,
                "month": scope.month,
                "grand_total_sum": money_str(cur_sum),
                "l0_count": len(current),
            },
            "previous": {
                "year": prev_year,
                "month": prev_month,
                "grand_total_sum": money_str(prev_sum),
                "l0_count": len(previous),
            },
            "delta": {
                "mom_delta": money_str(delta),
                "mom_rate": str(rate) if rate is not None else None,
            },
        }

    def _pack_steel(self, db: Session, scope: AnalysisScope) -> dict[str, Any]:
        page_size = min(STEEL_FETCH_LIMIT, 200)
        rows, total, _filters = self._steel.paginate(
            db,
            SteelPriceQuery(
                year=scope.year,
                month=scope.month,
                location=scope.location,
                page=1,
                size=page_size,
            ),
        )
        ranked = sorted(
            rows,
            key=lambda r: r.final_price_per_ton or Decimal("0"),
            reverse=True,
        )[:TOP_N]
        return {
            "row_count": total,
            "top_by_final_price": [
                pick(
                    vo_dump(row),
                    {
                        "steel_mill",
                        "category_name",
                        "grade",
                        "thickness",
                        "width",
                        "spec",
                        "final_price_per_ton",
                        "base_price",
                        "thickness_adjustment",
                        "width_adjustment",
                    },
                )
                for row in ranked
            ],
        }

    def _pack_stamping(self, db: Session, scope: AnalysisScope) -> dict[str, Any]:
        page_size = min(STAMPING_FETCH_LIMIT, 500)
        rows, total, _filters = self._stamping.paginate(
            db,
            StampingPartCostQuery(
                year=scope.year,
                month=scope.month,
                location=scope.location,
                vehicle_model=scope.vehicle_model,
                stamping_supplier=scope.stamping_supplier,
                page=1,
                size=page_size,
            ),
        )
        ranked = sorted(
            rows,
            key=lambda r: r.unit_cost or Decimal("0"),
            reverse=True,
        )[:TOP_N]
        partial = [row for row in rows if getattr(row, "calc_status", "ok") != "ok"]
        return {
            "row_count": total,
            "partial_count": len(partial),
            "top_by_unit_cost": [
                pick(
                    vo_dump(row),
                    {
                        "part_number",
                        "part_name",
                        "stamping_supplier",
                        "unit_cost",
                        "material_net_per_part",
                        "process_fee_amount",
                        "steel_mill",
                        "calc_status",
                    },
                )
                for row in ranked
            ],
        }

    def _pack_gate(self, db: Session, scope: AnalysisScope) -> dict[str, Any]:
        ready = self._engine.get_ready(
            db,
            location=scope.location,
            year=scope.year,
            month=scope.month,
        )
        gates = [vo_dump(item) for item in ready.gates.upload_or_config]
        for item in ready.gates.annual_derived:
            gates.append(vo_dump(item))
        message = (
            "引擎硬停，请先补齐主数据"
            if ready.gates.hard_stop
            else ("可启动核价" if ready.can_start else "门禁未完全通过")
        )
        return {
            "hard_stop": bool(ready.gates.hard_stop),
            "can_start": bool(ready.can_start),
            "message": message,
            "gates": gates,
        }

    def _pack_part_drilldown(
        self,
        db: Session,
        scope: AnalysisScope,
        l0_rows: list[L0AssemblyCostVO],
    ) -> dict[str, Any] | None:
        part_number = (scope.part_number or "").strip()
        if not part_number:
            return None
        match = next(
            (row for row in l0_rows if row.part_number == part_number),
            None,
        )
        if match is None:
            detail = self._l0.paginate(
                db,
                L0AssemblyCostQuery(
                    year=scope.year,
                    month=scope.month,
                    location=scope.location,
                    vehicle_model=scope.vehicle_model,
                    bom_version=scope.bom_version,
                    part_number=part_number,
                    skip=0,
                    limit=5,
                ),
            )[0]
            match = detail[0] if detail else None
        if match is None:
            return {
                "part_number": part_number,
                "message": "未找到该零件号的 L0 核价结果",
            }
        data = vo_dump(match)
        return pick(
            data,
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
                "calc_message",
                "missing_leaf_count",
                "items",
                "indirects",
            },
        )
