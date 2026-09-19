"""财务导出缺 L0 序号提示。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.costing.assembly_cost.export.workbook.missing_l0_seq import (
    MissingL0Seq,
    find_missing_l0_seqs,
    format_missing_l0_seq_note,
)


def test_format_missing_l0_seq_note_mentions_part_and_max() -> None:
    text = format_missing_l0_seq_note(
        [MissingL0Seq(seq_no=17, part_number="553000999AA")],
        export_count=43,
        universe_max_seq=44,
    )
    assert "缺序号 17（553000999AA）" in text
    assert "本表共 43 条" in text
    assert "勿按最大序号 44 当作件数" in text


def test_find_missing_l0_seqs_uses_bom_universe() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        SimpleNamespace(
            seq_no=16,
            part_number="501012536AA",
            effective_year=2025,
            effective_month=1,
        ),
        SimpleNamespace(
            seq_no=17,
            part_number="553000999AA",
            effective_year=2025,
            effective_month=1,
        ),
        SimpleNamespace(
            seq_no=18,
            part_number="553001000AA",
            effective_year=2025,
            effective_month=1,
        ),
        SimpleNamespace(
            seq_no=99,
            part_number="FUTUREAA",
            effective_year=2025,
            effective_month=6,
        ),
    ]
    records = [
        SimpleNamespace(source_node_id=1),
        SimpleNamespace(source_node_id=2),
    ]
    with patch(
        "app.services.costing.assembly_cost.export.workbook.missing_l0_seq.LocationService"
    ) as loc_cls:
        loc_cls.return_value.expand_for_query.return_value = ["芜湖"]
        missing, universe_max = find_missing_l0_seqs(
            db,
            records,
            year=2025,
            month=5,
            location="芜湖",
            vehicle_model="T13J",
            export_seq_nos={1: 16, 2: 18},
        )

    assert universe_max == 18
    assert missing == [MissingL0Seq(seq_no=17, part_number="553000999AA")]


def test_find_missing_skips_when_scope_incomplete() -> None:
    missing, universe_max = find_missing_l0_seqs(
        MagicMock(),
        [],
        year=2025,
        month=5,
        location="芜湖",
        vehicle_model=None,
    )
    assert missing == []
    assert universe_max is None
