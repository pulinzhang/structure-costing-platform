"""分析一次运行的结果容器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.llm.analysis.shared.constants import ANALYSIS_VERSION


@dataclass
class AnalysisRunResult:
    summary: dict[str, Any] | None = None
    result: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    has_data: bool = False
    data_message: str = ""
    comparability: str = "unknown"
    comparability_note: str | None = None
    anomaly_note: str | None = None
    analysis_version: str = ANALYSIS_VERSION
    filtered_missing_price_count: int = 0
