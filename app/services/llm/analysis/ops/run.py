"""作业台 / 模具费 / 检具费 / 采购对象 / 工程变更。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
)
from app.common.part_number import normalize_part_number_token
from app.repositories.llm.cost_analysis.repository import L0CostAnalysisRepository
from app.repositories.llm.cost_analysis.rows import L0PartPeriodRow
from app.repositories.llm.die_fee_analysis_repository import DieFeeAnalysisRepository
from app.repositories.llm.engineering_change_analysis_repository import (
    EngineeringChangeAnalysisRepository,
    EngineeringChangeRow,
)
from app.repositories.llm.engineering_change_effect_analysis_repository import (
    EngineeringChangeEffectAnalysisRepository,
    build_ec_downstream_completeness,
    build_ec_process_die_period,
)
from app.repositories.llm.gauge_fee_analysis_repository import GaugeFeeAnalysisRepository
from app.repositories.llm.ops_workbench_repository import OpsWorkbenchRepository
from app.repositories.llm.procurement_object_analysis_repository import (
    ProcurementObjectAnalysisRepository,
)
from app.repositories.llm.stamping_cost_analysis_repository import (
    StampingCostAnalysisRepository,
    StampingPartPeriodRow,
)
from app.schemas.llm.analysis_payload import (
    AnalysisResultLeafPayload,
    RiskEntry,
)
from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.analysis.ops.engineering_change import (
    DISCONTINUE_CHANGE_TYPES,
    build_ec_procurement_supplier_status,
    build_engineering_change_drilldown,
    build_engineering_change_price_comparison,
    build_engineering_change_risks,
    build_engineering_change_summary,
    build_not_install_assembly_impact,
    collect_compare_part_numbers,
    price_window_for_rows,
)
from app.services.llm.analysis.ops.masterdata import (
    build_die_fee_drilldown,
    build_die_fee_summary,
    build_gauge_fee_drilldown,
    build_gauge_fee_summary,
    build_procurement_object_drilldown,
    build_procurement_object_summary,
)
from app.services.llm.analysis.ops.workbench import (
    build_ops_workbench_risks,
    build_ops_workbench_summary,
)
from app.services.llm.analysis.shared.compose import compose_result
from app.services.llm.analysis.shared.result import AnalysisRunResult
from app.services.llm.comparison_basis import resolve_comparability
from app.services.llm.query.parser.subjects import (
    asks_ec_procurement_supplier_status,
    asks_engineering_change_discontinue,
    asks_engineering_change_downstream,
    asks_engineering_change_price_compare,
    asks_engineering_change_process_die_period,
)
from app.services.llm.query.time_range import question_has_explicit_time


class OpsAnalysis:
    def __init__(self) -> None:
        self._ops_workbench_repo = OpsWorkbenchRepository()
        self._die_fee_repo = DieFeeAnalysisRepository()
        self._gauge_fee_repo = GaugeFeeAnalysisRepository()
        self._procurement_object_repo = ProcurementObjectAnalysisRepository()
        self._engineering_change_repo = EngineeringChangeAnalysisRepository()
        self._engineering_change_effect_repo = EngineeringChangeEffectAnalysisRepository()
        self._l0_repo = L0CostAnalysisRepository()
        self._stamping_repo = StampingCostAnalysisRepository()

    def run_ops_workbench(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        boards = self._ops_workbench_repo.query_boards(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            year=tr.end_year,
            month=tr.end_month,
        )
        summary = build_ops_workbench_summary(boards)
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=any(row.row_count > 0 for row in boards),
            data_message=(
                f"待审核={summary['pending_audit_total']}，"
                f"未完成={summary['incomplete_total']}，"
                f"待确认外发={summary['pending_confirm_total']}"
            ),
            summary=summary,
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "risk" in query.analyses:
            parts_result["risk"] = build_ops_workbench_risks(summary)
        out.result = compose_result(parts_result, default_kind="summary")
        return out

    def run_stamping_die_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        part_token = query.part_number() or ""
        rows = self._die_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year,
            end_year=tr.end_year,
            part_number=part_token or None,
        )
        head = self._die_fee_repo.pick_best_row(rows, part_token=part_token) if part_token else None
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"模具费行={len(rows)}" if rows else "当前范围无模具费数据"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_die_fee_summary(rows)
        if "risk" in query.analyses and out.summary:
            pending = int(str(out.summary.get("pending_audit_count") or 0))
            zero = int(str(out.summary.get("zero_fee_count") or 0))
            risks: list[RiskEntry] = []
            if pending:
                risks.append(
                    {
                        "risk_type": "pending_audit",
                        "count": pending,
                        "message": "尚有模具费未审核",
                    }
                )
            if zero:
                risks.append(
                    {
                        "risk_type": "zero_fee",
                        "count": zero,
                        "message": "尚有模具费为 0",
                    }
                )
            parts_result["risk"] = {"kind": "risk", "risks": risks}
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_die_fee_drilldown(
                rows, part_token=part_token, head=head
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out

    def run_stamping_gauge_fee(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        part_token = query.part_number() or ""
        rows = self._gauge_fee_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            part_number=part_token or None,
        )
        head = (
            self._gauge_fee_repo.pick_best_row(rows, part_token=part_token) if part_token else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"检具费行={len(rows)}" if rows else "当前范围无检具费档案"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_gauge_fee_summary(rows)
        if "risk" in query.analyses and out.summary:
            zero = int(str(out.summary.get("zero_fee_count") or 0))
            invalid = int(str(out.summary.get("invalid_count") or 0))
            gauge_risks: list[RiskEntry] = []
            if zero:
                gauge_risks.append(
                    {
                        "risk_type": "zero_fee",
                        "count": zero,
                        "message": "尚有检具费为 0",
                    }
                )
            if invalid:
                gauge_risks.append(
                    {
                        "risk_type": "invalid_gauge",
                        "count": invalid,
                        "message": "尚有检具费档案非有效",
                    }
                )
            parts_result["risk"] = {"kind": "risk", "risks": gauge_risks}
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_gauge_fee_drilldown(
                rows, part_token=part_token, head=head
            )
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out

    def run_procurement_object(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        part_token = query.part_number() or ""
        rows = self._procurement_object_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            bom_version=query.bom_version(),
            part_number=part_token or None,
        )
        head = (
            self._procurement_object_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"采购对象行={len(rows)}" if rows else "当前范围无采购对象列表"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses:
            out.summary = build_procurement_object_summary(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_procurement_object_drilldown(
                rows, part_token=part_token, head=head
            )
        if "risk" in query.analyses and out.summary:
            pending_confirm = int(str(out.summary.get("pending_confirm_count") or 0))
            pending_audit = int(str(out.summary.get("pending_audit_count") or 0))
            anomaly = int(str(out.summary.get("anomaly_count") or 0))
            missing_supplier = int(str(out.summary.get("missing_supplier_count") or 0))
            risks: list[RiskEntry] = []
            if pending_confirm:
                risks.append(
                    {
                        "risk_type": "pending_confirm",
                        "count": pending_confirm,
                        "message": "尚有采购对象未确认外发/自制",
                    }
                )
            if pending_audit:
                risks.append(
                    {
                        "risk_type": "pending_audit",
                        "count": pending_audit,
                        "message": "尚有采购对象未审核",
                    }
                )
            if missing_supplier:
                missing_items = out.summary.get("missing_supplier_items")
                missing_supplier_items = missing_items if isinstance(missing_items, list) else []
                risks.append(
                    {
                        "risk_type": "missing_supplier",
                        "count": missing_supplier,
                        "message": "已确认外发但尚未指定供应商",
                        "sample_part_numbers": [
                            item.get("part_number")
                            for item in missing_supplier_items[:8]
                            if isinstance(item, dict)
                        ],
                        "missing_supplier_items": missing_supplier_items,
                        "truncated": bool(out.summary.get("missing_supplier_truncated")),
                    }
                )
            if anomaly:
                risks.append(
                    {
                        "risk_type": "procurement_anomaly",
                        "count": anomaly,
                        "message": "采购对象核对区仍有异常件",
                    }
                )
            parts_result["risk"] = {"kind": "risk", "risks": risks}
        default_kind = "drilldown" if part_token else "summary"
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out

    def run_engineering_change(self, db: Session, query: AnalysisQuery) -> AnalysisRunResult:
        tr = query.time_range
        part_token = query.part_number() or ""
        question = query.user_question or ""
        wants_price_compare = asks_engineering_change_price_compare(question) or (
            "comparison" in query.analyses
            and any(
                word in question for word in ("单价", "价格", "变更前", "变更后", "涨超", "构成")
            )
        )
        wants_supplier = asks_ec_procurement_supplier_status(question)
        wants_downstream = asks_engineering_change_downstream(question)
        wants_process_die = asks_engineering_change_process_die_period(question)
        wants_not_install_impact = asks_engineering_change_discontinue(question) and (
            "总成" in question or "影响" in question or "少装" in question
        )
        # 单件查旧号/停用：无明确时间则不按当月截断
        apply_time = question_has_explicit_time(question) or not part_token
        change_types: tuple[str, ...] | None = None
        if asks_engineering_change_discontinue(question):
            change_types = DISCONTINUE_CHANGE_TYPES
        elif "增加零件" in question or "新增零件" in question or "加了哪些" in question:
            change_types = (CHANGE_TYPE_ADD_PART,)
        elif "改图" in question and "此件不装" not in question:
            change_types = (CHANGE_TYPE_REVISE,)

        rows = self._engineering_change_repo.query_rows(
            db,
            location=query.location(),
            vehicle_model=query.vehicle_model(),
            start_year=tr.start_year if apply_time else None,
            start_month=tr.start_month if apply_time else None,
            end_year=tr.end_year if apply_time else None,
            end_month=tr.end_month if apply_time else None,
            part_number=part_token or None,
            change_types=change_types,
        )
        head = (
            self._engineering_change_repo.pick_best_row(rows, part_token=part_token)
            if part_token
            else None
        )
        out = AnalysisRunResult(
            comparability=resolve_comparability(query.comparison_basis),
            has_data=bool(rows),
            data_message=(f"工程变更行={len(rows)}" if rows else "当前范围无工程变更记录"),
        )
        parts_result: dict[str, AnalysisResultLeafPayload] = {}
        if "summary" in query.analyses or not part_token:
            out.summary = build_engineering_change_summary(rows)
        if "drilldown" in query.analyses or part_token:
            parts_result["drilldown"] = build_engineering_change_drilldown(
                rows, part_token=part_token, head=head
            )
        if "risk" in query.analyses or asks_engineering_change_discontinue(question):
            summary = out.summary or build_engineering_change_summary(rows)
            out.summary = summary
            parts_result["risk"] = build_engineering_change_risks(summary)
        if wants_price_compare and rows:
            parts_result["comparison"] = self._build_ec_price_comparison(db, query, rows)
            out.has_data = True
        if wants_not_install_impact and rows:
            not_install_rows = [row for row in rows if row.change_type == CHANGE_TYPE_NOT_INSTALL]
            if not_install_rows:
                parts_result["not_install_assembly_impact"] = (
                    self._build_not_install_assembly_impact(db, query, not_install_rows)
                )
                out.has_data = True
        if wants_supplier:
            procurement_rows = self._procurement_object_repo.query_rows(
                db,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                limit=5000,
            )
            prefer_add = "增加零件" in question or "新增零件" in question
            parts_result["ec_procurement_supplier"] = build_ec_procurement_supplier_status(
                rows,
                procurement_rows,
                prefer_add_part=prefer_add,
            )
            out.has_data = True
        if wants_downstream:
            downstream_rows = self._engineering_change_effect_repo.query_downstream_rows(
                db,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                start_year=tr.start_year if apply_time else None,
                start_month=tr.start_month if apply_time else None,
                end_year=tr.end_year if apply_time else None,
                end_month=tr.end_month if apply_time else None,
            )
            parts_result["ec_downstream"] = build_ec_downstream_completeness(downstream_rows)
            out.has_data = out.has_data or bool(downstream_rows)
        if wants_process_die:
            period_rows = self._engineering_change_effect_repo.query_process_die_period_rows(
                db,
                location=query.location(),
                vehicle_model=query.vehicle_model(),
                start_year=tr.start_year if apply_time else None,
                start_month=tr.start_month if apply_time else None,
                end_year=tr.end_year if apply_time else None,
                end_month=tr.end_month if apply_time else None,
            )
            parts_result["ec_process_die_period"] = build_ec_process_die_period(period_rows)
            out.has_data = out.has_data or bool(period_rows)
        default_kind = (
            "comparison"
            if wants_price_compare
            else (
                "ec_procurement_supplier"
                if wants_supplier
                else ("drilldown" if part_token else "summary")
            )
        )
        out.result = compose_result(parts_result, default_kind=default_kind)
        return out

    def _build_ec_price_comparison(
        self,
        db: Session,
        query: AnalysisQuery,
        rows: list[EngineeringChangeRow],
    ) -> AnalysisResultLeafPayload:
        part_numbers = collect_compare_part_numbers(rows)
        window = price_window_for_rows(rows)
        assembly_by_part: dict[str, list[L0PartPeriodRow]] = {}
        stamping_by_part: dict[str, list[StampingPartPeriodRow]] = {}
        if part_numbers and window is not None:
            start_year, start_month, end_year, end_month = window
            for part_number in part_numbers:
                key = normalize_part_number_token(part_number)
                assembly_by_part[key] = self._l0_repo.query_part_rows(
                    db,
                    location=query.location(),
                    vehicle_model=query.vehicle_model(),
                    bom_version=None,
                    start_year=start_year,
                    start_month=start_month,
                    end_year=end_year,
                    end_month=end_month,
                    part_number=part_number,
                    limit=50,
                    tree_root_only=False,
                )
                stamping_by_part[key] = self._stamping_repo.query_part_rows(
                    db,
                    location=query.location(),
                    vehicle_model=query.vehicle_model(),
                    start_year=start_year,
                    start_month=start_month,
                    end_year=end_year,
                    end_month=end_month,
                    part_number=part_number,
                    limit=50,
                )
        return build_engineering_change_price_comparison(
            rows,
            assembly_by_part=assembly_by_part,
            stamping_by_part=stamping_by_part,
        )

    def _build_not_install_assembly_impact(
        self,
        db: Session,
        query: AnalysisQuery,
        rows: list[EngineeringChangeRow],
    ) -> AnalysisResultLeafPayload:
        part_numbers = collect_compare_part_numbers(rows)
        for row in rows:
            asm = (row.after_assembly_part_number or "").strip() or (
                row.before_assembly_part_number or ""
            ).strip()
            if asm and asm not in part_numbers:
                part_numbers.append(asm)
        window = price_window_for_rows(rows)
        assembly_by_part: dict[str, list[L0PartPeriodRow]] = {}
        stamping_by_part: dict[str, list[StampingPartPeriodRow]] = {}
        if part_numbers and window is not None:
            start_year, start_month, end_year, end_month = window
            for part_number in part_numbers:
                key = normalize_part_number_token(part_number)
                assembly_by_part[key] = self._l0_repo.query_part_rows(
                    db,
                    location=query.location(),
                    vehicle_model=query.vehicle_model(),
                    bom_version=None,
                    start_year=start_year,
                    start_month=start_month,
                    end_year=end_year,
                    end_month=end_month,
                    part_number=part_number,
                    limit=50,
                    tree_root_only=False,
                )
                stamping_by_part[key] = self._stamping_repo.query_part_rows(
                    db,
                    location=query.location(),
                    vehicle_model=query.vehicle_model(),
                    start_year=start_year,
                    start_month=start_month,
                    end_year=end_year,
                    end_month=end_month,
                    part_number=part_number,
                    limit=50,
                )
        return build_not_install_assembly_impact(
            rows,
            assembly_by_part=assembly_by_part,
            stamping_by_part=stamping_by_part,
        )
