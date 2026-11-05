"""Pure-Python text chunking (no heavy dependencies, easy to unit test)."""
import re
from typing import List

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def _split_long(sentence: str, size: int) -> List[str]:
    """Hard-split a single oversized 'sentence' (tables, headers without punctuation) on whitespace."""
    if len(sentence) <= size:
        return [sentence]
    parts, current = [], ""
    for word in sentence.split():
        if current and len(current) + 1 + len(word) > size:
            parts.append(current)
            current = ""
        while len(word) > size:  # single token longer than a chunk
            parts.append(word[:size])
            word = word[size:]
        current = f"{current} {word}".strip()
    if current:
        parts.append(current)
    return parts


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Sentence-aware chunking with character overlap. No chunk exceeds `chunk_size` (plus one joining space)."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    sentences: List[str] = []
    for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")):
        if s.strip():
            sentences.extend(_split_long(s.strip(), chunk_size))

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for sent in sentences:
        if current and current_len + len(sent) + 1 > chunk_size:
            chunks.append(" ".join(current))
            carried, carried_len = [], 0
            for s in reversed(current):  # carry trailing sentences as overlap
                if carried_len + len(s) > overlap:
                    break
                carried.insert(0, s)
                carried_len += len(s) + 1
            current, current_len = carried, carried_len
        current.append(sent)
        current_len += len(sent) + 1
    if current:
        chunks.append(" ".join(current))
    return [c.strip() for c in chunks if c.strip()]
