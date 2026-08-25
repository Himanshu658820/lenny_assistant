from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.rag import ingest as ingest_module
from app.rag import retriever

router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/stats")
def stats():
    with SessionLocal() as db:
        documents = db.execute(select(func.count(Document.id))).scalar_one()
        chunks = db.execute(select(func.count(Chunk.id))).scalar_one()
    return {"documents": documents, "chunks": chunks}


@router.post("/ingest")
def ingest(limit: int = Query(default=0, ge=0, le=500)):
    return ingest_module.ingest_all(limit=limit)


@router.get("/search")
def search(q: str = Query(min_length=1), top_k: int = Query(default=6, ge=1, le=20)):
    results, supported = retriever.retrieve(q, top_k=top_k)
    return {"query": q, "supported": supported, "results": results}
