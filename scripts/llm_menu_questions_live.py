# -*- coding: utf-8 -*-
"""接通真实 LLM + 业务库，逐条跑菜单标准问句，校验解析 / 取数 / Snapshot。

用法（仓库根目录）::

    python -X utf8 scripts/llm_menu_questions_live.py
    python -X utf8 scripts/llm_menu_questions_live.py --with-report

需配置 .env 中 LLM_API_KEY / LLM_MODEL / LLM_BASE_URL。
"""

from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.database import DatabaseConfig  # noqa: E402
from app.services.llm.analysis.runner import AnalysisRunner  # noqa: E402
from app.services.llm.client import LlmClientError  # noqa: E402
from app.services.llm.context.snapshot_builder import SnapshotBuilder  # noqa: E402
from app.services.llm.generator import LlmReportGenerator  # noqa: E402
from app.services.llm.menu_catalog import SUBJECT_MENU  # noqa: E402
from app.services.llm.query.query_parser import QueryParser  # noqa: E402
from tests.llm.menu_question_matrix import (  # noqa: E402
    MENU_QUESTION_CASES,
    complete_cases,
)


@dataclass
class LiveCheckResult:
    menu_label: str
    user_question: str
    ok: bool = False
    subject: str = ""
    expected_subject: str = ""
    hash_page: str = ""
    time_range: str = ""
    location: str = ""
    has_data: bool = False
    data_message: str = ""
    report_chars: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _check_routing(result: LiveCheckResult, case, query) -> None:
    result.subject = query.subject
    result.expected_subject = case.expected_subject or ""
    result.hash_page = case.hash_page
    result.time_range = f"{query.time_range.start} ~ {query.time_range.end}"
    result.location = query.location() or ""

    if query.subject != case.expected_subject:
        result.errors.append(
            f"subject 期望 {case.expected_subject}，实际 {query.subject}"
        )

    menu = SUBJECT_MENU.get(case.expected_subject or "")
    if menu.hash_page != case.hash_page and case.expected_subject == "bom_material":
        if case.hash_page not in ("bom-structure", "bom-viz"):
            result.errors.append(f"hash_page 期望 #{case.hash_page}")
    elif menu.hash_page != case.hash_page:
        result.errors.append(
            f"hash_page 期望 #{case.hash_page}，菜单登记 #{menu.hash_page}"
        )

    if query.time_range.start != "2025-01" or query.time_range.end != "2025-01":
        result.errors.append(
            f"时间期望 2025-01，实际 {query.time_range.start}~{query.time_range.end}"
        )

    if case.expected_subject != "steel_price_policy" and not result.location:
        result.warnings.append("location 未对齐到青岛（LLM 可能未抽出基地）")
    elif result.location and result.location not in ("青岛", "青岛基地"):
        result.warnings.append(f"location 为 {result.location}，非青岛")


def _run_one(case, *, with_report: bool) -> LiveCheckResult:
    result = LiveCheckResult(
        menu_label=case.menu_label,
        user_question=case.user_question,
    )
    if case.status != "complete":
        result.warnings.append("pending 菜单，跳过路由断言")
        return result

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        parser = QueryParser()
        query = parser.parse(db, user_question=case.user_question)

        runner = AnalysisRunner()
        run = runner.run(db, query)
        snapshot = SnapshotBuilder().build(query=query, run=run)

        result.has_data = snapshot.meta.has_data
        result.data_message = snapshot.meta.data_message or ""

        _check_routing(result, case, query)

        if not snapshot.meta.has_data:
            result.warnings.append(f"无业务数据: {snapshot.meta.data_message}")
        elif snapshot.summary is None:
            result.errors.append("有数据但 summary 为空")

        if with_report:
            generator = LlmReportGenerator()
            try:
                generated = generator.generate(snapshot=snapshot, audience="buyer_lead")
                result.report_chars = len(generated.markdown_content or "")
                if result.report_chars < 80:
                    result.errors.append("报告正文过短")
            except LlmClientError as exc:
                fallback = generator.render_fallback_markdown(
                    snapshot=snapshot,
                    error_hint=str(exc),
                )
                result.report_chars = len(fallback)
                result.warnings.append(f"报告 LLM 失败，已降级: {exc}")

        result.ok = not result.errors
    except Exception as exc:
        result.errors.append(f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
    finally:
        db.close()

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM 菜单问句联调")
    parser.add_argument(
        "--with-report",
        action="store_true",
        help="额外调用报告生成 LLM（每条问句 2 次模型调用）",
    )
    args = parser.parse_args()

    if not settings.LLM_API_KEY.strip():
        print("错误: 未配置 LLM_API_KEY（.env）")
        return 2

    print(
        f"LLM 联调 | model={settings.LLM_MODEL} | "
        f"base={settings.LLM_BASE_URL} | report={args.with_report}\n"
    )
    print(f"{'结果':<6} {'菜单':<20} {'subject':<20} {'数据':<6} 说明")
    print("-" * 100)

    results: list[LiveCheckResult] = []
    for case in complete_cases():
        live = _run_one(case, with_report=args.with_report)
        results.append(live)
        status = "PASS" if live.ok else "FAIL"
        data_flag = "有" if live.has_data else "无"
        note = live.data_message[:40] if live.data_message else ""
        if live.errors:
            note = live.errors[0][:60]
        print(
            f"{status:<6} {live.menu_label:<20} "
            f"{live.subject:<20} {data_flag:<6} {note}"
        )

    print("-" * 100)
    print("\n明细：")
    for live in results:
        print(f"\n■ {live.menu_label}")
        print(f"  问句: {live.user_question}")
        print(f"  subject: {live.subject} (期望 {live.expected_subject})")
        print(f"  列表页: #{live.hash_page}")
        print(f"  时间: {live.time_range} | 基地: {live.location or '—'}")
        print(f"  数据: {'有' if live.has_data else '无'} — {live.data_message}")
        if args.with_report:
            print(f"  报告: {live.report_chars} 字")
        for warning in live.warnings:
            print(f"  ⚠ {warning}")
        for error in live.errors:
            print(f"  ✗ {error}")

    pending = [case for case in MENU_QUESTION_CASES if case.status == "pending"]
    if pending:
        print("\n待接 subject（未跑 LLM 断言）:")
        for case in pending:
            print(f"  - {case.menu_label}: {case.user_question}")

    failed = sum(1 for item in results if not item.ok)
    warned = sum(1 for item in results if item.warnings)
    print(
        f"\n汇总: {len(results) - failed}/{len(results)} 路由通过, "
        f"{warned} 条有警告, {failed} 条失败"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
