"""LLM 分析切片 Schema（Query / Snapshot）。"""

from app.schemas.llm.analysis_query import (
    AnalysisQuery,
    ComparisonBasis,
    TimeRange,
)
from app.schemas.llm.analysis_snapshot import AnalysisSnapshot, SnapshotMeta

__all__ = [
    "AnalysisQuery",
    "ComparisonBasis",
    "TimeRange",
    "AnalysisSnapshot",
    "SnapshotMeta",
]
