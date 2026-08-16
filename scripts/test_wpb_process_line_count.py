"""
焊接工艺拆解 — 后端功能测试（清空表后跑）

覆盖：
1) 解析：无过程量 items=[] → process_line_count 可 =0
2) L0 annotate：保留 unparsed/partial + qa_note（不计成 anomaly）
3) 生成落库：process_line_count == 明细行数
4) 筛 / HUD：process_line_count_eq=0、l0_zero_process_count

用法（仓库根目录）::

    python -X utf8 -m scripts.test_wpb_process_line_count
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER
from app.database import DatabaseConfig
from app.models.bom import BomNode, BomSnapshot
from app.parsers.bom.welding_process_breakdown_parser import parse_welding_info_text
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownGenerateDTO,
    BomWeldingProcessBreakdownQuery,
)
from app.services.bom.welding_process_breakdown.bom_tree import annotate_parse_status
from app.services.bom.welding_process_breakdown.generate_service import (
    BomWeldingProcessBreakdownGenerateService,
)
from app.services.bom.welding_process_breakdown.service import (
    BomWeldingProcessBreakdownService,
)

LOCATION = "青岛"
VEHICLE_MODEL = "T28"
BOM_VERSION = "D/00"
BAD_WELD = "随便写点看不懂的工艺描述"
PARTIAL_WELD = "电泳+喷粉（黑色）"


def _fail(msg: str) -> None:
    raise AssertionError(msg)


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def clear_tables(db: Session) -> None:
    db.execute(text("DELETE FROM bom_welding_process_breakdown_line"))
    db.execute(text("DELETE FROM bom_welding_process_breakdown_node"))
    db.execute(text("DELETE FROM bom_welding_process_breakdown_generate_logs"))
    db.commit()
    print("cleared: node / line / generate_logs")


def test_parser_and_annotate() -> None:
    print("\n[1] parser + annotate")
    r = parse_welding_info_text("焊点：10 凸焊：2")
    assert len(r.items) == 2 and r.parse_status == "ok", r
    _ok("正常原文 → 2 items / ok")

    r = parse_welding_info_text(BAD_WELD)
    assert len(r.items) == 0 and r.parse_status == "unparsed", r
    st, note = annotate_parse_status(
        level=0, has_children=True, base_parse_status=r.parse_status
    )
    assert st == "unparsed" and note and "计费异常" in note, (st, note)
    _ok("L0 未识别 → unparsed + qa_note（非 anomaly）")

    st1, _ = annotate_parse_status(
        level=1, has_children=False, base_parse_status=r.parse_status
    )
    assert st1 == "unparsed", st1
    _ok("L1 未识别 → 保持 unparsed")

    r = parse_welding_info_text(PARTIAL_WELD)
    assert len(r.items) == 0 and r.parse_status == "partial", r
    st, note = annotate_parse_status(
        level=0, has_children=True, base_parse_status=r.parse_status
    )
    assert st == "partial" and note and "计费异常" in note, (st, note)
    _ok("L0 仅标签无过程量 → partial + qa_note / items=[]")

    r = parse_welding_info_text("")
    assert len(r.items) == 0 and r.parse_status == "unparsed", r
    _ok("空串 → unparsed / 无假行")


def _pick_two_l0(db: Session) -> tuple[BomNode, BomNode, BomSnapshot]:
    snap = (
        db.query(BomSnapshot)
        .filter(
            BomSnapshot.location == LOCATION,
            BomSnapshot.vehicle_model == VEHICLE_MODEL,
            BomSnapshot.bom_version == BOM_VERSION,
        )
        .first()
    )
    if not snap:
        _fail(f"缺少 BOM 快照 {LOCATION}/{VEHICLE_MODEL}/{BOM_VERSION}")
    l0s = (
        db.query(BomNode)
        .filter(BomNode.snapshot_id == snap.id, BomNode.level == 0)
        .order_by(BomNode.id)
        .all()
    )
    with_weld = [n for n in l0s if (n.weld_info or "").strip()]
    if len(with_weld) < 2:
        _fail(f"L0 带焊接原文不足 2 条，实际 {len(with_weld)}")
    return with_weld[0], with_weld[1], snap


def test_generate_and_zero_filter(db: Session) -> None:
    print("\n[2] generate + process_line_count + L0=0 筛选")
    node_bad, node_partial, _snap = _pick_two_l0(db)
    orig_bad = node_bad.weld_info
    orig_partial = node_partial.weld_info
    print(
        f"  inject bad L0={node_bad.part_number}, "
        f"partial L0={node_partial.part_number}"
    )
    try:
        node_bad.weld_info = BAD_WELD
        node_partial.weld_info = PARTIAL_WELD
        db.commit()

        gen = BomWeldingProcessBreakdownGenerateService()
        result, err = gen.generate(
            db,
            BomWeldingProcessBreakdownGenerateDTO(
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
            ),
            SYSTEM_USER,
        )
        if err or result is None:
            _fail(f"generate failed: {err}")
        print(
            f"  generated nodes={result.node_count} lines={result.line_count}"
        )
        _ok("生成成功")

        repo = BomWeldingProcessBreakdownRepository()
        nodes = repo.list_by_scope(
            db,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
        )
        assert nodes, "主表为空"

        mismatches: list[str] = []
        for n in nodes:
            real_lines = list(n.lines or [])
            if n.process_line_count != len(real_lines):
                mismatches.append(
                    f"{n.part_number} count={n.process_line_count} "
                    f"real={len(real_lines)}"
                )
        if mismatches:
            _fail("计数不一致: " + "; ".join(mismatches[:5]))
        _ok("全部 process_line_count == 明细行数")

        bad_row = next(
            (n for n in nodes if n.part_number == node_bad.part_number), None
        )
        partial_row = next(
            (n for n in nodes if n.part_number == node_partial.part_number), None
        )
        if not bad_row or not partial_row:
            _fail("注入的 L0 未出现在拆解主表")

        assert bad_row.level == 0
        assert bad_row.process_line_count == 0, bad_row.process_line_count
        assert bad_row.parse_status == "unparsed", bad_row.parse_status
        assert bad_row.qa_note and "计费异常" in bad_row.qa_note
        _ok(f"坏原文 L0 {bad_row.part_number}: count=0 / unparsed")

        assert partial_row.process_line_count == 0, partial_row.process_line_count
        assert partial_row.parse_status == "partial", partial_row.parse_status
        assert partial_row.qa_note and "计费异常" in partial_row.qa_note
        _ok(f"仅标签 L0 {partial_row.part_number}: count=0 / partial")

        zeros, zero_total = repo.paginate(
            db,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            process_line_count_eq=0,
            skip=0,
            limit=100,
        )
        zero_parts = {n.part_number for n in zeros}
        assert node_bad.part_number in zero_parts
        assert node_partial.part_number in zero_parts
        assert zero_total >= 2
        _ok(f"process_line_count_eq=0 → {zero_total} 条，含注入的两台 L0")

        summary = repo.summarize_by_filters(
            db,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
        )
        summary["l0_zero_process_count"] = repo.count_by_filters(
            db,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            level=0,
            process_line_count_eq=0,
        )
        assert summary["l0_zero_process_count"] >= 2, summary
        l0_zeros = sum(
            1 for n in nodes if n.level == 0 and n.process_line_count == 0
        )
        assert summary["l0_zero_process_count"] == l0_zeros, (
            summary["l0_zero_process_count"],
            l0_zeros,
        )
        _ok(f"summary.l0_zero_process_count={summary['l0_zero_process_count']}")

        svc = BomWeldingProcessBreakdownService()
        vos, total, filters = svc.paginate(
            db,
            BomWeldingProcessBreakdownQuery(
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                level=0,
                process_line_count_eq=0,
                page=1,
                size=50,
            ),
        )
        assert total >= 2
        assert all(v.level == 0 and v.process_line_count == 0 for v in vos)
        assert filters["summary"]["l0_zero_process_count"] >= 2
        _ok(f"Service 分页 L0+eq0 → {total} 条 VO")

    finally:
        node_bad.weld_info = orig_bad
        node_partial.weld_info = orig_partial
        db.commit()
        print("  restored BOM weld_info")


def regenerate_clean(db: Session) -> None:
    print("\n[3] 恢复后重新生成干净数据")
    clear_tables(db)
    gen = BomWeldingProcessBreakdownGenerateService()
    result, err = gen.generate(
        db,
        BomWeldingProcessBreakdownGenerateDTO(
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
        ),
        SYSTEM_USER,
    )
    if err or result is None:
        _fail(f"clean generate failed: {err}")
    repo = BomWeldingProcessBreakdownRepository()
    summary = repo.summarize_by_filters(
        db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
    )
    summary["l0_zero_process_count"] = repo.count_by_filters(
        db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
        level=0,
        process_line_count_eq=0,
    )
    print(
        f"  clean nodes={result.node_count} lines={result.line_count} "
        f"summary={summary}"
    )
    assert summary["l0_zero_process_count"] == 0, summary
    _ok("干净数据 L0 工艺数=0 为 0")


def main() -> int:
    test_parser_and_annotate()
    SessionLocal = DatabaseConfig.get_session_factory()
    db = SessionLocal()
    try:
        clear_tables(db)
        test_generate_and_zero_filter(db)
        regenerate_clean(db)
    finally:
        db.close()
    print("\nALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
