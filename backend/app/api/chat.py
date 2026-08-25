import logging

from fastapi import APIRouter
from sqlalchemy import select

from app.agents import orchestrator
from app.api.schemas import ArtifactOut, ChatRequest, ChatResponse, SourceOut
from app.config import settings
from app.core.errors import LLMProviderError, SessionNotFoundError
from app.db.models import ChatSession, Message, utcnow
from app.db.session import SessionLocal
from app.llm.base import ChatMessage
from app.llm.factory import get_provider
import json

from fastapi.responses import StreamingResponse

from app.agents.skills import grounded_chat
from app.core.errors import AppError

logger = logging.getLogger("lenny.chat")

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    provider = get_provider(payload.llm_provider)

    if provider.name == "anthropic" and not settings.anthropic_api_key:
        raise LLMProviderError(
            "ANTHROPIC_API_KEY is not configured. Set it in .env or switch LLM_PROVIDER to ollama."
        )
    if provider.name == "openai" and not settings.openai_api_key:
        raise LLMProviderError(
            "OPENAI_API_KEY is not configured. Set it in .env or switch LLM_PROVIDER to ollama."
        )

    with SessionLocal() as db:
        if payload.session_id:
            session = db.execute(
                select(ChatSession).where(ChatSession.id == payload.session_id)
            ).scalar_one_or_none()

            if session is None:
                raise SessionNotFoundError(str(payload.session_id))
        else:
            session = ChatSession(
                title=payload.message[:80], llm_provider=provider.name
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        history_rows = (
            db.execute(
                select(Message)
                .where(Message.session_id == session.id)
                .order_by(Message.created_at.desc())
                .limit(8)
            )
            .scalars()
            .all()
        )

        history = [
            ChatMessage(role=m.role, content=m.content) for m in reversed(history_rows)
        ]

        outcome = orchestrator.run(payload.message, history, provider)

        db.add(Message(session_id=session.id, role="user", content=payload.message))
        db.add(
            Message(
                session_id=session.id,
                role="assistant",
                content=outcome["answer"],
                sources=outcome["sources"],
                meta={
                    "skill": outcome["skill"],
                    "provider": outcome["provider"],
                    "model": outcome["model"],
                    "latency_ms": outcome["latency_ms"],
                    "supported": outcome["supported"],
                    "checks": outcome.get("checks"),
                    "artifact": outcome.get("artifact"),
                },
            )
        )
        session.updated_at = utcnow()
        db.commit()
        session_id = session.id

    logger.info(
        "chat session=%s provider=%s skill=%s supported=%s latency_ms=%d",
        session_id,
        outcome["provider"],
        outcome["skill"],
        outcome["supported"],
        outcome["latency_ms"],
    )

    return ChatResponse(
        session_id=session_id,
        answer=outcome["answer"],
        skill=outcome["skill"],
        supported=outcome["supported"],
        sources=[SourceOut(**s) for s in outcome["sources"]],
        artifact=(
            ArtifactOut(**outcome["artifact"]) if outcome.get("artifact") else None
        ),
        provider=outcome["provider"],
        model=outcome["model"],
        latency_ms=outcome["latency_ms"],
    )


@router.post("/chat/stream")
def chat_stream(payload: ChatRequest):
    provider = get_provider(payload.llm_provider)

    if provider.name == "anthropic" and not settings.anthropic_api_key:
        raise LLMProviderError(
            "ANTHROPIC_API_KEY is not configured. Set it in .env or switch LLM_PROVIDER to ollama."
        )
    if provider.name == "openai" and not settings.openai_api_key:
        raise LLMProviderError(
            "OPENAI_API_KEY is not configured. Set it in .env or switch LLM_PROVIDER to ollama."
        )

    model_label = {
        "ollama": settings.ollama_chat_model,
        "anthropic": settings.anthropic_model,
        "openai": settings.openai_model,
    }.get(provider.name, provider.name)

    def sse(name: str, data) -> str:
        return f"event: {name}\ndata: {json.dumps(data)}\n\n"

    def generate():
        with SessionLocal() as db:
            if payload.session_id:
                session = db.execute(
                    select(ChatSession).where(ChatSession.id == payload.session_id)
                ).scalar_one_or_none()
                if session is None:
                    yield sse(
                        "error", {"message": f"Session not found: {payload.session_id}"}
                    )
                    return
            else:
                session = ChatSession(
                    title=payload.message[:80], llm_provider=provider.name
                )
                db.add(session)
                db.commit()
                db.refresh(session)

            history_rows = (
                db.execute(
                    select(Message)
                    .where(Message.session_id == session.id)
                    .order_by(Message.created_at.desc())
                    .limit(8)
                )
                .scalars()
                .all()
            )
            history = [
                ChatMessage(role=m.role, content=m.content)
                for m in reversed(history_rows)
            ]

            db.add(Message(session_id=session.id, role="user", content=payload.message))
            db.commit()
            session_id = session.id

        yield sse("session", {"session_id": str(session_id)})

        skill_name = orchestrator.route(payload.message)
        sources: list = []
        supported = True
        artifact = None
        full_answer = ""

        if skill_name == "grounded_chat":
            results, supported, messages = grounded_chat.build_prompt(
                payload.message, history
            )
            sources = results
            yield sse("sources", sources)

            if not supported:
                full_answer = grounded_chat.UNSUPPORTED_ANSWER
                yield sse("token", {"text": full_answer})
            else:
                buffer: list[str] = []
                try:
                    for token in provider.chat_stream(messages):
                        buffer.append(token)
                        yield sse("token", {"text": token})
                except AppError as exc:
                    yield sse("error", {"message": exc.message})
                    return
                full_answer = "".join(buffer)
        else:
            # Ship 30 / artifact skills run whole (they need validation), then deliver
            outcome = orchestrator.run(payload.message, history, provider)
            sources = outcome["sources"]
            supported = outcome["supported"]
            artifact = outcome.get("artifact")
            full_answer = outcome["answer"]
            yield sse("sources", sources)
            yield sse("token", {"text": full_answer})
            if artifact:
                yield sse("artifact", artifact)

        with SessionLocal() as db:
            db.add(
                Message(
                    session_id=session_id,
                    role="assistant",
                    content=full_answer,
                    sources=sources,
                    meta={
                        "skill": skill_name,
                        "provider": provider.name,
                        "model": model_label,
                        "supported": supported,
                        "artifact": artifact,
                    },
                )
            )
            sess = db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            ).scalar_one()
            sess.updated_at = utcnow()
            db.commit()

        yield sse(
            "done",
            {
                "session_id": str(session_id),
                "answer": full_answer,
                "skill": skill_name,
                "supported": supported,
                "sources": sources,
                "artifact": artifact,
                "provider": provider.name,
            },
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
