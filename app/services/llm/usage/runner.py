"""UsageHelpRunner：不查核价库，只检索 helper 语料。"""

from __future__ import annotations

from app.schemas.llm.analysis_query import AnalysisQuery
from app.services.llm.analysis.runner import AnalysisRunResult
from app.services.llm.query.intent_router import detect_help_topic
from app.services.llm.usage.manifest import retrieve_chunks


class UsageHelpRunner:
    def run(self, query: AnalysisQuery) -> AnalysisRunResult:
        topic = query.help_topic or detect_help_topic(query.user_question)
        chunks = retrieve_chunks(query.user_question, primary_topic=topic, top_k=3)
        titles = [chunk.title for chunk in chunks]
        run = AnalysisRunResult(
            comparability="unknown",
            has_data=bool(chunks),
            data_message=(
                f"命中帮助语料：{'、'.join(titles)}" if chunks else "未命中帮助语料，已回退快速入门"
            ),
            summary={
                "kind": "usage_help",
                "help_topic": topic,
                "matched_titles": titles,
                "chunk_count": len(chunks),
            },
            result={
                "kind": "usage_help",
                "help_topic": topic,
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "title": chunk.title,
                        "excerpt": chunk.text[:800],
                        "help_url": chunk.help_url,
                    }
                    for chunk in chunks
                ],
            },
            evidence={
                "corpus_chunks": [chunk.to_dict() for chunk in chunks],
                "help_topic": topic,
            },
        )
        return run
