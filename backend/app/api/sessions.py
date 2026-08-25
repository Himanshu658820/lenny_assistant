import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.schemas import MessageOut, SessionCreate, SessionOut
from app.config import settings
from app.core.errors import SessionNotFoundError
from app.db.models import ChatSession, Message
from app.db.session import SessionLocal

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _to_out(session: ChatSession, count: int) -> SessionOut:
    return SessionOut(
        id=session.id,
        title=session.title,
        llm_provider=session.llm_provider,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=count,
    )


def _get_session_or_404(db, session_id: uuid.UUID) -> ChatSession:
    session = db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    ).scalar_one_or_none()

    if session is None:
        raise SessionNotFoundError(str(session_id))

    return session


@router.post("", response_model=SessionOut, status_code=201)
def create_session(payload: SessionCreate):
    with SessionLocal() as db:
        session = ChatSession(
            title=payload.title,
            llm_provider=payload.llm_provider or settings.llm_provider,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return _to_out(session, 0)


@router.get("", response_model=list[SessionOut])
def list_sessions(limit: int = Query(default=50, ge=1, le=100)):
    with SessionLocal() as db:
        rows = db.execute(
            select(ChatSession, func.count(Message.id))
            .outerjoin(Message, Message.session_id == ChatSession.id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        ).all()

    return [_to_out(session, count) for session, count in rows]


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def get_messages(session_id: uuid.UUID):
    with SessionLocal() as db:
        _get_session_or_404(db, session_id)
        messages = (
            db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at)
            )
            .scalars()
            .all()
        )

    return [MessageOut.model_validate(m) for m in messages]


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: uuid.UUID):
    with SessionLocal() as db:
        session = _get_session_or_404(db, session_id)
        db.delete(session)
        db.commit()
    return None
