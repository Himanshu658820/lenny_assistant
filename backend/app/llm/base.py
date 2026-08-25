from dataclasses import dataclass
from typing import Iterator


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class ChatResult:
    content: str
    provider: str
    model: str
    latency_ms: int
    usage: dict | None = None


class BaseLLMProvider:
    name: str = "base"

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        raise NotImplementedError

    def chat_stream(self, messages: list[ChatMessage]) -> Iterator[str]:
        # Default fallback: yield the full non-streamed answer as one chunk
        yield self.chat(messages).content
