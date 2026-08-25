import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    llm_provider: str | None = Field(default=None, max_length=50)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    llm_provider: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SourceOut(BaseModel):
    title: str
    source_path: str
    heading: str | None = None
    score: float


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    sources: list[SourceOut] | None = None
    meta: dict | None = None
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: uuid.UUID | None = None
    llm_provider: str | None = Field(default=None, max_length=50)


class ArtifactOut(BaseModel):
    type: str  # "markdown" | "html"
    title: str
    content: str
    word_count: int | None = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    skill: str
    supported: bool
    sources: list[SourceOut]
    artifact: ArtifactOut | None = None
    provider: str
    model: str
    latency_ms: int
