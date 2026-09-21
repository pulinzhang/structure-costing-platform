"""基于业务库现有数据，穷举 LLM 可答问句并跑通解析 → 分析 → 报告（或降级）。

用法（仓库根目录）::

    python -X utf8 scripts/llm_full_data_audit.py
    python -X utf8 scripts/llm_full_data_audit.py --with-report
    python -X utf8 scripts/llm_full_data_audit.py --with-report --json-out tests/llm/last_full_audit.json

无 LLM_API_KEY 时报告层走规则降级，仍可校验取数与 Snapshot。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.common.part_number import is_temporal_part_number_token  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import DatabaseConfig  # noqa: E402
from app.services.llm.analysis.runner import AnalysisRunner  # noqa: E402
from app.services.llm.client.openai_compatible import LlmClientError  # noqa: E402
from app.services.llm.context.snapshot_builder import SnapshotBuilder  # noqa: E402
from app.services.llm.generator import LlmReportGenerator  # noqa: E402
from app.services.llm.menu_catalog import SUBJECT_MENU  # noqa: E402
from app.services.llm.query.parser.pipeline import QueryParser  # noqa: E402
from app.services.llm.usage.runner import UsageHelpRunner  # noqa: E402
from tests.llm.traversal_question_matrix import (  # noqa: E402
    TraversalCase,
    TraversalScope,
    _pick_scope,
    build_traversal_cases,
    mock_extractor_draft,
)

SUSPICIOUS_REPORT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"作为\s*AI", "自称 AI 助手"),
    (r"我无法访问", "声称无法访问数据"),
    (r"没有(?:实时)?数据", "否认有数据（可能与 has_data 矛盾）"),
)


@dataclass
class AuditCase:
    case_id: str
    category: str
    user_question: str
    expected_subject: str | None = None
    expected_hash_page: str | None = None
    expect_has_data: bool | None = None
    time_start: str | None = None
    time_end: str | None = None
    compare_locations: tuple[str, ...] = ()


@dataclass
class AuditResult:
    case_id: str
    category: str
    user_question: str
    ok: bool = False
    subject: str = ""
    query_mode: str = ""
    analyses: list[str] = field(default_factory=list)
    time_start: str = ""
    time_end: str = ""
    location: str = ""
    vehicle_model: str = ""
    has_data: bool = False
    data_message: str = ""
    parser_data_message: str = ""
    comparability: str = ""
    report_chars: int = 0
    report_preview: str = ""
    used_fallback: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def build_cases(db) -> list[AuditCase]:
    cases: list[AuditCase] = []
    for item in build_traversal_cases(db):
        cases.append(
            AuditCase(
                case_id=item.case_id,
                category=item.category,
                user_question=item.user_question,
                expected_subject=item.expected_subject,
                expected_hash_page=item.expected_hash_page,
                expect_has_data=item.expect_has_data,
                time_start=item.time_start,
                time_end=item.time_end,
                compare_locations=item.compare_locations,
            )
        )
    return cases


def _audit_report_text(
    text: str,
    *,
    has_data: bool,
    used_fallback: bool,
) -> list[str]:
    issues: list[str] = []
    if not text or len(text.strip()) < 40:
        issues.append("报告正文过短或为空")
    if has_data and len(text.strip()) < 80:
        issues.append("有数据但报告正文不足 80 字")
    for pattern, label in SUSPICIOUS_REPORT_PATTERNS:
        if re.search(pattern, text):
            if pattern == r"没有(?:实时)?数据" and not has_data:
                continue
            if pattern == r"\d{4,}" and used_fallback:
                continue
            issues.append(f"可疑表述: {label}")
    return issues


def run_case(
    db,
    case: AuditCase,
    *,
    with_report: bool,
    scope: TraversalScope,
    mock_extractor: bool,
    parser: QueryParser,
    runner: AnalysisRunner,
    usage_runner: UsageHelpRunner,
    snapshot_builder: SnapshotBuilder,
    generator: LlmReportGenerator | None,
) -> AuditResult:
    result = AuditResult(
        case_id=case.case_id,
        category=case.category,
        user_question=case.user_question,
    )
    try:
        if mock_extractor and case.category != "usage":
            traversal_stub = TraversalCase(
                case_id=case.case_id,
                category=case.category,
                user_question=case.user_question,
                expected_subject=case.expected_subject,
                expected_hash_page=case.expected_hash_page,
                time_start=case.time_start,
                time_end=case.time_end,
                compare_locations=case.compare_locations,
                expect_has_data=case.expect_has_data,
            )
            draft = mock_extractor_draft(traversal_stub, scope)
            parser._extractor.extract = lambda *args, **kwargs: draft

        query = parser.parse(db, user_question=case.user_question)
        result.subject = query.subject
        result.query_mode = query.query_mode
        result.analyses = list(query.analyses)
        result.time_start = query.time_range.start
        result.time_end = query.time_range.end
        result.location = query.location() or ""
        result.vehicle_model = query.vehicle_model() or ""
        result.parser_data_message = query.parser_data_message or ""

        part_number = query.part_number()
        if part_number and is_temporal_part_number_token(part_number):
            result.errors.append(f"误将时间识别为零件号: {part_number}")

        if case.expected_subject and query.subject != case.expected_subject:
            result.errors.append(f"subject 期望 {case.expected_subject}，实际 {query.subject}")

        if case.expected_hash_page and case.expected_subject:
            menu = SUBJECT_MENU.get(case.expected_subject)
            if menu:
                expected_page = case.expected_hash_page
                if case.expected_subject == "bom_material" and expected_page in (
                    "bom-structure",
                    "bom-viz",
                ):
                    expected_page = "bom-material"
                if menu.hash_page != expected_page:
                    result.errors.append(f"列表页期望 {expected_page}，实际 {menu.hash_page}")

        if query.query_mode == "usage_help":
            run = usage_runner.run(query)
            snapshot = snapshot_builder.build(query=query, run=run)
            result.has_data = snapshot.meta.has_data
            result.data_message = snapshot.meta.data_message or ""
        else:
            run = runner.run(db, query)
            snapshot = snapshot_builder.build(query=query, run=run)
            result.has_data = snapshot.meta.has_data
            result.data_message = snapshot.meta.data_message or ""
            result.comparability = snapshot.meta.comparability or ""

            if snapshot.meta.has_data and snapshot.summary is None:
                result.errors.append("有数据但 summary 为空")

        if case.expect_has_data is True and not result.has_data:
            result.errors.append(f"期望有数据: {result.data_message}")
        if case.expect_has_data is False and result.has_data:
            result.errors.append("期望无数据但 has_data=True")

        if with_report and generator is not None:
            used_fallback = False
            try:
                if not settings.LLM_API_KEY.strip():
                    markdown = generator.render_fallback_markdown(
                        snapshot=snapshot,
                        error_hint="未配置 LLM_API_KEY",
                    )
                    used_fallback = True
                else:
                    generated = generator.generate(
                        snapshot=snapshot,
                        audience="buyer_lead",
                    )
                    markdown = generated.markdown_content or ""
            except LlmClientError as exc:
                markdown = generator.render_fallback_markdown(
                    snapshot=snapshot,
                    error_hint=str(exc),
                )
                used_fallback = True
                result.warnings.append(f"LLM 失败已降级: {exc}")

            result.report_chars = len(markdown)
            result.report_preview = markdown[:240].replace("\n", " ")
            result.used_fallback = used_fallback
            report_issues = _audit_report_text(
                markdown,
                has_data=result.has_data,
                used_fallback=used_fallback,
            )
            result.errors.extend(report_issues)

        if not result.has_data and case.category == "menu" and case.expect_has_data is True:
            result.warnings.append(f"菜单问句无数据: {result.data_message}")

        result.ok = not result.errors
    except Exception as exc:
        result.errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 全量数据审计")
    parser.add_argument("--with-report", action="store_true", help="生成报告（或降级）")
    parser.add_argument(
        "--mock-extractor",
        action="store_true",
        help="用遍历矩阵 mock 条件抽取（与 pytest 遍历一致，避免默认 2026 年）",
    )
    parser.add_argument("--json-out", type=str, default="", help="结果 JSON 路径")
    args = parser.parse_args()

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    scope = _pick_scope(db)
    cases = build_cases(db)
    db.close()

    print(
        f"LLM 全量审计 | cases={len(cases)} | report={args.with_report} | "
        f"mock_extractor={args.mock_extractor} | "
        f"scope={scope.location} {scope.anchor_ym} | "
        f"llm_key={'yes' if settings.LLM_API_KEY.strip() else 'no(fallback)'}\n"
    )

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    query_parser = QueryParser()
    runner = AnalysisRunner()
    usage_runner = UsageHelpRunner()
    snapshot_builder = SnapshotBuilder()
    generator = LlmReportGenerator() if args.with_report else None

    results: list[AuditResult] = []
    try:
        for case in cases:
            result = run_case(
                db,
                case,
                with_report=args.with_report,
                scope=scope,
                mock_extractor=args.mock_extractor,
                parser=query_parser,
                runner=runner,
                usage_runner=usage_runner,
                snapshot_builder=snapshot_builder,
                generator=generator,
            )
            results.append(result)
            status = "PASS" if result.ok else "FAIL"
            data_flag = "有" if result.has_data else "无"
            note = (
                result.errors[0]
                if result.errors
                else (
                    result.data_message[:36] if result.data_message else result.report_preview[:36]
                )
            )
            print(
                f"{status:<6} [{result.category}] {result.case_id:<22} "
                f"{result.subject:<18} {data_flag:<3} {note}"
            )
    finally:
        db.close()

    failed = [r for r in results if not r.ok]
    warned = [r for r in results if r.warnings]
    no_data_menu = [
        r
        for r in results
        if r.category == "menu" and not r.has_data and r.query_mode != "usage_help"
    ]

    print("\n" + "=" * 100)
    print(
        f"汇总: {len(results) - len(failed)}/{len(results)} 通过, "
        f"{len(warned)} 条警告, {len(failed)} 条失败"
    )
    if no_data_menu:
        print(f"菜单问句无数据: {len(no_data_menu)} 条（可能库内缺表数据）")

    if failed:
        print("\n失败明细:")
        for item in failed:
            print(f"\n■ {item.case_id} ({item.category})")
            print(f"  问句: {item.user_question}")
            for err in item.errors:
                print(f"  ✗ {err}")
            for warn in item.warnings:
                print(f"  ⚠ {warn}")

    if args.json_out:
        out_path = Path(args.json_out)
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "llm_key_configured": bool(settings.LLM_API_KEY.strip()),
            "total": len(results),
            "failed": len(failed),
            "warned": len(warned),
            "results": [asdict(r) for r in results],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 已写入: {out_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
