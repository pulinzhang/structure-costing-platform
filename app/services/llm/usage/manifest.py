"""manifest 关键词检索：按问句打分选语料。"""

from __future__ import annotations

from app.services.llm.usage.corpus import CorpusChunk, load_corpus_chunks


def _score_chunk(question: str, chunk: CorpusChunk, *, primary_topic: str | None) -> int:
    text = (question or "").strip().lower()
    if not text:
        return 0

    score = 0
    if primary_topic and chunk.chunk_id == primary_topic:
        score += 100
    if primary_topic and primary_topic.startswith("faq_") and chunk.chunk_id == primary_topic:
        score += 100

    for keyword in chunk.keywords:
        key = keyword.lower()
        if key in text or keyword in question:
            score += 10 + min(len(key), 20)

    if chunk.title and chunk.title in question:
        score += 15

    return score


def retrieve_chunks(
    question: str,
    *,
    primary_topic: str | None = None,
    top_k: int = 3,
) -> list[CorpusChunk]:
    """按关键词命中返回 top_k 语料；至少返回 primary_topic 对应块（若有）。"""
    chunks = list(load_corpus_chunks())
    if not chunks:
        return []

    ranked = sorted(
        chunks,
        key=lambda chunk: _score_chunk(question, chunk, primary_topic=primary_topic),
        reverse=True,
    )
    positive = [chunk for chunk in ranked if _score_chunk(question, chunk, primary_topic=primary_topic) > 0]

    if primary_topic:
        primary = next((chunk for chunk in chunks if chunk.chunk_id == primary_topic), None)
        if primary is not None:
            result = [primary]
            for chunk in positive:
                if chunk.chunk_id != primary.chunk_id and chunk not in result:
                    result.append(chunk)
                if len(result) >= top_k:
                    break
            return result[:top_k]

    if positive:
        return positive[:top_k]

    start = next((chunk for chunk in chunks if chunk.chunk_id == "start"), None)
    return [start] if start else ranked[:1]
