import hashlib
import logging
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.llm.ollama import embed_texts
from app.rag.chunking import chunk_markdown

logger = logging.getLogger("lenny.ingest")


def _extract_title(raw: str, path: Path) -> str:
    for line in raw.splitlines():
        if line.startswith("# "):
            return line[2:].strip()[:300]
    return path.stem.replace("-", " ").replace("_", " ")[:300]


def ingest_all(limit: int = 0) -> dict:
    root = Path(settings.transcripts_dir)
    files = sorted(root.rglob("*.md")) if root.exists() else []

    if limit > 0:
        files = files[:limit]

    summary = {
        "files_seen": len(files),
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "chunks_added": 0,
    }

    with SessionLocal() as db:
        for path in files:
            raw = path.read_text(encoding="utf-8", errors="replace")
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            rel = path.as_posix()

            existing = db.execute(
                select(Document).where(Document.source_path == rel)
            ).scalar_one_or_none()

            if existing and existing.sha256 == digest:
                summary["skipped"] += 1
                continue

            if existing:
                db.delete(existing)
                db.flush()
                summary["updated"] += 1
            else:
                summary["added"] += 1

            doc = Document(
                source_path=rel,
                title=_extract_title(raw, path),
                sha256=digest,
                word_count=len(raw.split()),
            )
            db.add(doc)
            db.flush()

            drafts = chunk_markdown(raw, settings.chunk_size, settings.chunk_overlap)
            embed_inputs = [
                f"Episode: {doc.title}\nSection: {d.heading or 'general'}\n{d.content}"
                for d in drafts
            ]
            vectors = embed_texts(embed_inputs) if drafts else []

            for index, (draft, vector) in enumerate(zip(drafts, vectors)):
                db.add(
                    Chunk(
                        document_id=doc.id,
                        chunk_index=index,
                        heading=draft.heading,
                        content=draft.content,
                        embedding=vector,
                    )
                )
                summary["chunks_added"] += 1

            logger.info("ingested document path=%s chunks=%d", rel, len(drafts))

        db.commit()

    logger.info("ingestion complete %s", summary)
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    print(ingest_all(limit=args.limit))
