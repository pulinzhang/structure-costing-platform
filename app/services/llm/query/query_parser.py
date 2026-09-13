"""对外入口：问句 → AnalysisQuery。实现在 parser/。"""

from app.services.llm.query.parser.pipeline import QueryParser

__all__ = ["QueryParser"]
