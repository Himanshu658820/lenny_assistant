import logging

from app.llm.base import ChatMessage
from app.rag import retriever

logger = logging.getLogger("lenny.skill.grounded_chat")

SYSTEM_PROMPT = (
    "You are the Lenny Growth Assistant, an internal assistant for a product and growth team. "
    "Answer strictly using the transcript excerpts provided below. "
    "When you use a specific idea from an excerpt, cite it by naming the episode or title in parentheses. "
    "Keep answers practical and specific. "
    "Answer only the latest user question; use earlier turns only to resolve pronouns or follow-ups, "
    "and never repeat or continue a previous answer. "
    "Produce one consistent stance: never say the excerpts do not mention a topic and then cite them about it. "
    "If the excerpts do not address the question's topic, or do not contain enough information, "
    "say clearly that the material does not support an answer instead of forcing one."
)

UNSUPPORTED_ANSWER = (
    "I couldn't find support for that in the Lenny podcast transcripts I have indexed. "
    "I'd rather tell you that than guess. Try asking about topics covered in the show — "
    "for example retention, onboarding, growth loops, positioning, or PM career skills."
)


def _dedupe(results: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for r in results:
        key = r["title"]
        if key not in best or r["score"] > best[key]["score"]:
            best[key] = r
    return list(best.values())


def build_prompt(message: str, history: list[ChatMessage]):
    """Returns (sources, supported, llm_messages)."""
    results, supported = retriever.retrieve(message)
    results = _dedupe(results)

    if not supported:
        return results, False, None

    context = "\n\n".join(
        f"[Source {i + 1}] {r['title']} — {r['heading'] or 'transcript excerpt'}\n{r['content']}"
        for i, r in enumerate(results)
    )

    messages = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    messages.extend(history[-8:])
    messages.append(
        ChatMessage(
            role="user",
            content=f"Transcript excerpts:\n{context}\n\nQuestion: {message}",
        )
    )
    return results, True, messages


def run(message: str, history: list[ChatMessage], provider) -> dict:
    results, supported, messages = build_prompt(message, history)

    if not supported:
        logger.info("grounded_chat unsupported query=%s", message)
        return {
            "answer": UNSUPPORTED_ANSWER,
            "sources": [],
            "supported": False,
            "skill": "grounded_chat",
            "provider": provider.name,
            "model": "none",
            "latency_ms": 0,
        }

    result = provider.chat(messages)

    return {
        "answer": result.content,
        "sources": [
            {
                "title": r["title"],
                "source_path": r["source_path"],
                "heading": r["heading"],
                "score": r["score"],
            }
            for r in results
        ],
        "supported": True,
        "skill": "grounded_chat",
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
    }
