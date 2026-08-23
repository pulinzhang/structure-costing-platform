# -*- coding: utf-8 -*-
"""按侧栏菜单打印标准问句，并校验 QueryParser 路由（不调真实 LLM）。

用法:
    python -X utf8 scripts/llm_menu_questions.py          # mock 路由
    python -X utf8 scripts/llm_menu_questions_live.py       # 真实 LLM + 库
    python -X utf8 scripts/llm_menu_questions_live.py --with-report
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.llm.menu_catalog import SUBJECT_MENU  # noqa: E402
from app.services.llm.query.query_parser import QueryParser  # noqa: E402
from tests.llm.menu_question_matrix import MENU_QUESTION_CASES  # noqa: E402


def _mock_parser(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V1"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2025-01"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )


def main() -> int:
    parser = QueryParser()
    db = MagicMock()
    _mock_parser(parser)

    print("侧栏列表页标准问句（青岛基地 + 2025年01月 + 主题）\n")
    print(f"{'状态':<8} {'菜单':<22} {'问句'}")
    print("-" * 80)

    failed = 0
    for case in MENU_QUESTION_CASES:
        query = parser.parse(db, user_question=case.user_question)
        status = case.status.upper()
        question = case.user_question

        if case.status == "complete":
            menu = SUBJECT_MENU.get(case.expected_subject or "")
            ok = query.subject == case.expected_subject and menu.hash_page == case.hash_page
            if not ok:
                failed += 1
                status = "FAIL"
            route = f" → {query.subject} / #{case.hash_page}"
        else:
            route = " → (待接 subject)"

        print(f"{status:<8} {case.menu_label:<22} {question}{route}")

    print("-" * 80)
    if failed:
        print(f"失败 {failed} 条")
        return 1
    print("全部 complete 条目路由正确")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
