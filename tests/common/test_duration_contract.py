"""运行历史耗时契约：秒数公式 + 守卫清单。"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta
from pathlib import Path

from app.common.duration import duration_seconds
from app.schemas.vo.timing import DurationSecondsMixin, calc_history_timing_vo_types

_VO_ROOT = Path(__file__).resolve().parents[2] / "app" / "schemas" / "vo"
_HISTORY_SUFFIXES = ("CalcLogVO", "GenerateLogVO", "RunVO", "RunListItemVO", "RunStepVO")


def test_duration_seconds_both_ends() -> None:
    start = datetime(2026, 1, 1, 12, 0, 0)
    end = start + timedelta(seconds=45)
    assert duration_seconds(start, end) == 45


def test_duration_seconds_missing_end_is_none() -> None:
    start = datetime(2026, 1, 1, 12, 0, 0)
    assert duration_seconds(start, None) is None
    assert duration_seconds(None, start) is None
    assert duration_seconds(None, None) is None


def test_duration_seconds_never_negative() -> None:
    start = datetime(2026, 1, 1, 12, 0, 10)
    end = datetime(2026, 1, 1, 12, 0, 0)
    assert duration_seconds(start, end) == 0


def test_calc_history_vos_expose_started_finished_duration() -> None:
    """四年后加新历史页：漏登记或漏 mixin 会在这里红。"""
    for vo_cls in calc_history_timing_vo_types():
        field_names = set(vo_cls.model_fields)
        assert "started_at" in field_names, f"{vo_cls.__name__} 缺 started_at"
        assert "finished_at" in field_names, f"{vo_cls.__name__} 缺 finished_at"
        assert issubclass(
            vo_cls, DurationSecondsMixin
        ), f"{vo_cls.__name__} 须继承 DurationSecondsMixin，禁止各 VO 自写秒数公式"
        schema_props = vo_cls.model_json_schema(mode="serialization").get("properties", {})
        assert (
            "duration_seconds" in schema_props
        ), f"{vo_cls.__name__} 序列化 schema 须含 duration_seconds（OpenAPI / 前端契约）"


def _discover_history_vo_names() -> set[str]:
    names: set[str] = set()
    for path in _VO_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if any(node.name.endswith(suffix) for suffix in _HISTORY_SUFFIXES):
                # 引擎相关只收 CostingEngine*，避免误伤其它 RunVO
                if node.name.endswith(("RunVO", "RunListItemVO", "RunStepVO")) and (
                    not node.name.startswith("CostingEngine")
                ):
                    continue
                names.add(node.name)
    return names


def test_registry_covers_discovered_history_vo_names() -> None:
    """新 *CalcLogVO / *GenerateLogVO / CostingEngine*Run* 漏登记会红。"""
    registered = {cls.__name__ for cls in calc_history_timing_vo_types()}
    discovered = _discover_history_vo_names()
    missing = sorted(discovered - registered)
    extra = sorted(registered - discovered)
    assert not missing, f"须登记进 calc_history_timing_vo_types: {missing}"
    assert not extra, f"登记册有多余名（类已删或改名）: {extra}"
