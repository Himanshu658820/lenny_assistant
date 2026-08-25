import logging
import re

from app.llm.base import ChatMessage
from app.rag import retriever

logger = logging.getLogger("lenny.skill.artifact")

HTML_RULES = (
    "Produce ONE complete HTML document with inline <style> CSS in the <head>. "
    "No JavaScript, no external resources, no forms. "
    "Use a clean modern layout: system font stack, generous spacing, one accent color."
)

MD_RULES = (
    "Produce a complete, well-structured Markdown document with a title, headings, bullets, "
    "and bold emphasis where useful."
)


def _wants_html(message: str) -> bool:
    lowered = message.lower()
    return any(k in lowered for k in ("html", "css", "dashboard", "webpage", "landing"))


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:html|markdown|md)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def run(message: str, history: list[ChatMessage], provider) -> dict:
    want_html = _wants_html(message)

    results, supported = retriever.retrieve(message)
    context = (
        "\n\n".join(
            f"[Source {i + 1}] {r['title']}\n{r['content']}"
            for i, r in enumerate(results)
        )
        if supported
        else "(No transcript context available; rely on the conversation.)"
    )

    conversation = "\n".join(f"{m.role}: {m.content[:400]}" for m in history[-6:])

    rules = HTML_RULES if want_html else MD_RULES
    system = (
        "You are an artifact generator inside the Lenny Growth Assistant. "
        f"{rules} "
        "Base content on the conversation and any provided transcript excerpts. "
        "Return ONLY the document content, with no explanations."
    )

    user = (
        f"Conversation so far:\n{conversation or '(none)'}\n\n"
        f"Transcript excerpts:\n{context}\n\n"
        f"Request: {message}"
    )

    result = provider.chat(
        [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ]
    )
    content = _strip_fences(result.content)

    artifact = {
        "type": "html" if want_html else "markdown",
        "title": message[:60],
        "content": content,
        "word_count": len(re.findall(r"\w+", content)),
    }

    sources = (
        [
            {
                "title": r["title"],
                "source_path": r["source_path"],
                "heading": r["heading"],
                "score": r["score"],
            }
            for r in results
        ]
        if supported
        else []
    )

    logger.info("artifact type=%s words=%d", artifact["type"], artifact["word_count"])

    return {
        "answer": f"I've generated a {artifact['type']} artifact: “{artifact['title']}”.",
        "sources": sources,
        "supported": supported,
        "skill": "artifact",
        "artifact": artifact,
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
    }
