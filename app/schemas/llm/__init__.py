"""LLM 分析切片 Schema（Query / Snapshot / Payload / Draft）。"""

from app.schemas.llm.analysis_payload import (
    AnalysisResultPayload,
    AnalysisSummaryBag,
    ComparisonPayload,
    DrilldownPayload,
    DriversPayload,
    EvidencePayload,
    RiskPayload,
    SummaryPayload,
    TrendPayload,
)
from app.schemas.llm.analysis_query import (
    AnalysisQuery,
    ComparisonBasis,
    TimeRange,
)
from app.schemas.llm.analysis_snapshot import AnalysisSnapshot, SnapshotMeta
from app.schemas.llm.parser_draft import ParserDraft

__all__ = [
    "AnalysisQuery",
    "AnalysisResultPayload",
    "AnalysisSnapshot",
    "AnalysisSummaryBag",
    "ComparisonBasis",
    "ComparisonPayload",
    "DriversPayload",
    "DrilldownPayload",
    "EvidencePayload",
    "ParserDraft",
    "RiskPayload",
    "SnapshotMeta",
    "SummaryPayload",
    "TimeRange",
    "TrendPayload",
]
