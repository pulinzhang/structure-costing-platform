"""核价引擎进度权重映射（设计 §9.4）。"""

from __future__ import annotations


# (stage_start_pct, stage_end_pct)
STAGE_BANDS: dict[str, tuple[int, int]] = {
    "gate_plan": (0, 5),
    "annual": (5, 25),
    "steel": (25, 40),
    "part_cost": (40, 70),
    "l0": (70, 95),
    "summary": (95, 100),
}


def map_progress(stage: str, done: int, total: int) -> int:
    """同阶段多 scope：base + weight * (done / total)。"""
    start, end = STAGE_BANDS.get(stage, (0, 100))
    if total <= 0:
        return end
    ratio = max(0.0, min(1.0, done / total))
    return int(start + (end - start) * ratio)


def clamp_progress(value: int) -> int:
    return max(0, min(100, int(value)))
