import logging
import re

from app.llm.base import ChatMessage
from app.rag import retriever

logger = logging.getLogger("lenny.skill.ship30")

WORD_TARGET = 1250
WORD_RANGE = (1000, 1500)

PRINCIPLES = {
    "hook": "Open with a strong hook (contrarian claim, vivid anecdote, or surprising number). No preamble.",
    "narrative": "Follow a clear progression: problem -> tension -> insight -> application. One idea per section.",
    "skimmable": "Use descriptive H2/H3 headings, bullets for lists, and bold only for the few phrases that matter.",
    "takeaway": "End with a section titled 'The takeaway' with one specific, actionable recommendation.",
    "grounding": "Ground every non-obvious claim in the provided transcript excerpts and cite the episode/title in parentheses.",
    "voice": "Write like a practitioner talking to peers: direct, concrete, no fluff.",
}

SYSTEM_PROMPT = (
    "You are a Ship 30 for 30 essayist writing for a product and growth team.\n"
    + "\n".join(f"- {key}: {value}" for key, value in PRINCIPLES.items())
    + f"\n- length: about {WORD_TARGET} words."
)

UNSUPPORTED_ANSWER = (
    "I can't write a grounded Ship 30 essay on that topic from the transcripts I have indexed. "
    "Pick a topic covered in Lenny's podcast — retention, onboarding, growth loops, positioning, PM skills."
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _clean_topic(message: str) -> str:
    pattern = r"(write|create|draft|generate|a|an|please|ship\s*30(?:\s*for\s*30)?|essay|about|on|of)"
    topic = re.sub(pattern, " ", message, flags=re.IGNORECASE)
    topic = re.sub(r"\s+", " ", topic).strip(" .!?'\"")
    return topic or message


def _validate(essay: str) -> dict:
    words = _word_count(essay)
    return {
        "word_count": words,
        "within_length": WORD_RANGE[0] <= words <= WORD_RANGE[1],
        "has_headings": bool(re.search(r"^#{1,3} ", essay, re.M)),
        "has_bullets": bool(re.search(r"^\s*[-*] ", essay, re.M)),
        "has_bold": "**" in essay,
        "has_takeaway": "takeaway" in essay.lower(),
    }


def run(message: str, history: list[ChatMessage], provider) -> dict:
    topic = _clean_topic(message)
    results, supported = retriever.retrieve(topic)

    if not supported:
        logger.info("ship30 unsupported topic=%s", topic)
        return {
            "answer": UNSUPPORTED_ANSWER,
            "sources": [],
            "supported": False,
            "skill": "ship30",
            "artifact": None,
            "provider": provider.name,
            "model": "none",
            "latency_ms": 0,
        }

    context = "\n\n".join(
        f"[Source {i + 1}] {r['title']} — {r['heading'] or 'excerpt'}\n{r['content']}"
        for i, r in enumerate(results)
    )

    messages = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    messages.extend(history[-4:])
    messages.append(
        ChatMessage(
            role="user",
            content=f"Topic: {topic}\n\nTranscript excerpts:\n{context}\n\nWrite the essay now, in Markdown.",
        )
    )

    result = provider.chat(messages)
    essay = result.content
    checks = _validate(essay)

    if not checks["within_length"]:
        logger.info("ship30 length retry words=%d", checks["word_count"])
        retry = provider.chat(
            messages
            + [
                ChatMessage(role="assistant", content=essay),
                ChatMessage(
                    role="user",
                    content=(
                        f"The draft is {checks['word_count']} words. Rewrite it to about {WORD_TARGET} words "
                        "(between 1000 and 1500), keeping the same structure, citations, and takeaway."
                    ),
                ),
            ]
        )
        essay = retry.content
        result = retry
        checks = _validate(essay)

    logger.info("ship30 topic=%s checks=%s", topic, checks)

    return {
        "answer": f"Here is your Ship 30 for 30 essay on “{topic}”.",
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
        "skill": "ship30",
        "artifact": {
            "type": "markdown",
            "title": f"Ship 30: {topic[:60]}",
            "content": essay,
            "word_count": checks["word_count"],
        },
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "checks": checks,
    }
