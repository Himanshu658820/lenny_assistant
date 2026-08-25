from dataclasses import dataclass


@dataclass
class ChunkDraft:
    heading: str
    content: str


def chunk_markdown(
    text: str, chunk_size: int = 1200, overlap: int = 150
) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    current_heading = ""
    buffer = ""

    def flush() -> None:
        nonlocal buffer
        if buffer.strip():
            chunks.append(ChunkDraft(heading=current_heading, content=buffer.strip()))
        buffer = ""

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current_heading = line.lstrip("#").strip()
            continue

        if buffer and len(buffer) + len(line) > chunk_size:
            chunks.append(ChunkDraft(heading=current_heading, content=buffer.strip()))
            buffer = buffer[-overlap:] + "\n" + line
        else:
            buffer = line if not buffer else buffer + "\n" + line

    flush()
    return [c for c in chunks if len(c.content) >= 80]
