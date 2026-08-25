import re

SMALLTALK_RE = re.compile(
    r"^("
    r"h+[iey]+h*"
    r"|hello+"
    r"|yo|sup|howdy"
    r"|good\s+(morning|afternoon|evening)"
    r"|thanks?|thank\s+you"
    r"|who\s+are\s+you|what\s+can\s+you\s+do|help"
    r"|how\s+are\s+you"
    r"|nice\s+to\s+meet\s+you"
    r"|my\s+name\s+is\s+.+"
    r"|call\s+me\s+.+"
    r")[\s!.?]*$",
    re.IGNORECASE,
)

NAME_RE = re.compile(
    r"(?:my\s+name\s+is|call\s+me)\s+([a-zA-Z][a-zA-Z\s.]{1,40})", re.IGNORECASE
)

GREETING_ANSWER = (
    "Hey! I'm the Lenny Growth Assistant. I answer product and growth questions using "
    "Lenny's podcast transcripts, write Ship 30 for 30 essays, and generate Markdown/HTML "
    "artifacts. Try asking: “How do I improve retention?” or “Write a Ship 30 essay about onboarding.”"
)


def is_smalltalk(message: str) -> bool:
    return bool(SMALLTALK_RE.match(message.strip()))


def run(message: str, history, provider) -> dict:
    name_match = NAME_RE.search(message)

    if name_match:
        name = " ".join(name_match.group(1).split()).title()
        answer = (
            f"Nice to meet you, {name}! I'm the Lenny Growth Assistant. "
            "Ask me product or growth questions grounded in Lenny's podcast transcripts, "
            "request a Ship 30 for 30 essay, or ask for a Markdown/HTML artifact."
        )
    else:
        answer = GREETING_ANSWER

    return {
        "answer": answer,
        "sources": [],
        "supported": True,
        "skill": "smalltalk",
        "provider": provider.name,
        "model": "none",
        "latency_ms": 0,
    }
