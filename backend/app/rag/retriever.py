import logging

from sqlalchemy import func, select

from app.config import settings
from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.llm.ollama import embed_texts

logger = logging.getLogger("lenny.retrieval")


def retrieve(query: str, top_k: int | None = None) -> tuple[list[dict], bool]:
    top_k = top_k or settings.top_k

    with SessionLocal() as db:
        total = db.execute(select(func.count(Chunk.id))).scalar_one()
        if total == 0:
            return [], False

    vector = embed_texts([query])[0]

    with SessionLocal() as db:
        distance = Chunk.embedding.cosine_distance(vector)
        stmt = (
            select(
                Chunk.content,
                Chunk.heading,
                Chunk.chunk_index,
                Document.title,
                Document.source_path,
                distance.label("distance"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .order_by(distance)
            .limit(top_k)
        )
        rows = db.execute(stmt).all()

    results = [
        {
            "title": r.title,
            "source_path": r.source_path,
            "heading": r.heading,
            "chunk_index": r.chunk_index,
            "score": round(1.0 - float(r.distance), 4),
            "content": r.content,
        }
        for r in rows
    ]

    supported = bool(results) and results[0]["score"] >= settings.relevance_threshold
    logger.info(
        "retrieval query=%s results=%d supported=%s", query, len(results), supported
    )
    return results, supported
